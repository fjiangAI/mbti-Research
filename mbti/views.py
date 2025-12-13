from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Question, Response, Result, Questionnaire, TypeProfile
from .services import MBTIScoringService
from .services_standard import StandardMBTIScoringService
import json
import logging
import re

logger = logging.getLogger(__name__)



def home_view(request):
    """主页视图：展示MBTI测试入口和16种性格类型"""
    # 检查用户是否有测试结果
    has_result = False
    latest_result = None
    if request.user.is_authenticated:
        latest_result = Result.objects.filter(user=request.user).order_by('-created_at').first()
        has_result = latest_result is not None
    
    # MBTI 16种类型的图标映射（用于展示）
    TYPE_ICONS = {
        'INTJ': '🧠', 'INTP': '🔬', 'ENTJ': '🧭', 'ENTP': '🎤',
        'INFJ': '🛡️', 'INFP': '🎭', 'ENFJ': '🎯', 'ENFP': '🌟',
        'ISTJ': '📋', 'ISFJ': '🛡️', 'ESTJ': '📊', 'ESFJ': '🤝',
        'ISTP': '🔧', 'ISFP': '🎨', 'ESTP': '⚡', 'ESFP': '🎭',
    }
    
    # 从数据库读取16种类型数据，如果没有则使用默认值
    profiles = TypeProfile.objects.all().order_by('code')
    type_list = []
    
    for profile in profiles:
        # 使用数据库中的名称和描述，如果没有则使用简短描述
        name = profile.name if profile.name else profile.code
        desc = profile.description[:50] if profile.description else f'{name}类型的人格特点'
        type_list.append({
            'icon': TYPE_ICONS.get(profile.code, '⭐'),
            'title': name,
            'code': profile.code,
            'desc': desc,
        })
    
    # 如果没有数据库记录，使用默认列表（向后兼容）
    if not type_list:
        type_list = [
            {'icon': '🧠', 'title': '建筑师', 'code': 'INTJ', 'desc': '富有策略与远见，擅长系统化思考与规划'},
            {'icon': '🔬', 'title': '逻辑学家', 'code': 'INTP', 'desc': '好奇心强、热爱探索，追求逻辑与知识的边界'},
            {'icon': '🧭', 'title': '指挥官', 'code': 'ENTJ', 'desc': '果断、组织能力强，擅长目标导向与资源协调'},
            {'icon': '🎤', 'title': '辩论家', 'code': 'ENTP', 'desc': '思维灵活、善于辩论，热衷挑战与创新观点'},
            {'icon': '🛡️', 'title': '提倡者', 'code': 'INFJ', 'desc': '理想主义者，富有同情心，追求意义与价值'},
            {'icon': '🎭', 'title': '调停者', 'code': 'INFP', 'desc': '创造力强、价值观驱动，追求真实与和谐'},
            {'icon': '🎯', 'title': '主人公', 'code': 'ENFJ', 'desc': '天生的领导者，善于激励他人实现潜能'},
            {'icon': '🌟', 'title': '竞选者', 'code': 'ENFP', 'desc': '热情洋溢、富有创意，善于发现可能性'},
            {'icon': '📋', 'title': '物流师', 'code': 'ISTJ', 'desc': '实用主义的事实家，可靠性毋庸置疑'},
            {'icon': '🛡️', 'title': '守护者', 'code': 'ISFJ', 'desc': '非常专注、温暖的守护者，时刻准备保护爱的人'},
            {'icon': '📊', 'title': '总经理', 'code': 'ESTJ', 'desc': '出色的管理者，在管理事物或人员方面无与伦比'},
            {'icon': '🤝', 'title': '执政官', 'code': 'ESFJ', 'desc': '极有同情心、受欢迎、总是热心帮助他人'},
            {'icon': '🔧', 'title': '鉴赏家', 'code': 'ISTP', 'desc': '大胆而实际的实验家，擅长使用各种工具'},
            {'icon': '🎨', 'title': '探险家', 'code': 'ISFP', 'desc': '灵活、迷人的艺术家，时刻准备探索新的可能性'},
            {'icon': '⚡', 'title': '企业家', 'code': 'ESTP', 'desc': '聪明、精力充沛、善于感知的企业家，真正享受生活'},
            {'icon': '🎭', 'title': '娱乐家', 'code': 'ESFP', 'desc': '自发的、精力充沛的娱乐家，生活在他们周围从不无聊'},
        ]
    
    return render(request, 'mbti/home.html', {
        'has_result': has_result,
        'latest_result': latest_result,
        'type_list': type_list,
    })


@login_required
def test_view(request):
    # 检查用户是否已有测试结果
    has_result = Result.objects.filter(user=request.user).exists()
    retake = request.GET.get('retake', 'false').lower() == 'true'
    
    # 检查session中是否有测试答案（说明用户正在测试中）
    has_test_in_progress = False
    if hasattr(request, 'session') and 'test_answers' in request.session:
        test_answers = request.session.get('test_answers', {})
        # 如果session中有答案，说明用户正在测试中
        if test_answers:
            has_test_in_progress = True
    
    # 只有在用户已有结果、不是重新测试、且没有正在进行的测试时，才重定向
    # 注意：提交测试后session会被清除，所以这里不会误判
    if has_result and not retake and not has_test_in_progress:
        # 用户已有结果且不是重新测试，也没有正在进行的测试，重定向到结果页
        logger.info(f"用户 {request.user.username} 已有测试结果，重定向到结果页")
        return redirect('mbti:result')
    
    # 分页处理（需要先获取page_number来判断是否是第一次访问）
    try:
        page_number = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page_number = 1
    
    # 如果是重新测试，且是第一次访问（page=1），才清除之前的答案和session
    # 翻页时不应该清除数据！
    if retake and page_number == 1:
        # 清除session中的答案
        if hasattr(request, 'session') and 'test_answers' in request.session:
            del request.session['test_answers']
            request.session.modified = True
            logger.info(f"用户 {request.user.username} 重新测试，已清除session中的答案")
        
        # 清除旧的Response记录（重新测试时应该从头开始）
        qnn_temp = Questionnaire.objects.filter(is_active=True).first()
        if qnn_temp:
            deleted_count = Response.objects.filter(user=request.user, questionnaire=qnn_temp).delete()[0]
            logger.info(f"用户 {request.user.username} 重新测试，已清除 {deleted_count} 条旧的Response记录")
    
    qnn = Questionnaire.objects.filter(is_active=True).first()
    questions = Question.objects.filter(active=True, questionnaire=qnn).order_by('order', 'id') if qnn else Question.objects.filter(active=True).order_by('order', 'id')
    
    # 检查是否有题目
    if not questions.exists():
        messages.error(request, '暂可用测试题目，请联系管理员。')
        return redirect('mbti:home')
    
    # 分页处理（page_number已在上面获取）
    
    paginator = Paginator(questions, MBTIScoringService.QUESTIONS_PER_PAGE)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        # 如果页码不是整数，显示第一页
        page_obj = paginator.page(1)
        page_number = 1
    except EmptyPage:
        # 如果页码超出范围，显示最后一页
        page_obj = paginator.page(paginator.num_pages)
        page_number = paginator.num_pages
    
    # 注意：删除了页面跳转检查逻辑
    # 原因：正常翻页时，前端会先保存答案再跳转，但检查逻辑容易因为数据库写入延迟而误判
    # 提交时会统一检查所有题目是否完成，所以这里不需要检查
    
    # 获取已保存的答案（优先从数据库读取，然后从session补充）
    saved_answers = {}
    
    # 先从数据库读取已保存的Response
    if qnn:
        existing_responses = Response.objects.filter(
            user=request.user,
            questionnaire=qnn,
            question_id__in=questions.values_list('id', flat=True)
        )
        for resp in existing_responses:
            saved_answers[resp.question_id] = str(resp.choice)
    
    # 然后从session补充（session会覆盖数据库中的同名答案）
    if hasattr(request, 'session'):
        raw_answers = request.session.get('test_answers', {})
        for k, v in raw_answers.items():
            try:
                if isinstance(k, str) and k.startswith('q_'):
                    qid = int(k.split('_')[1])
                    saved_answers[qid] = str(v)
            except Exception:
                continue
    
    # 检查是否使用标准MBTI题库
    use_standard_mbti = qnn and qnn.key == 'mbti_standard_93'
    
    # 如果是标准MBTI，解析题目文本提取A/B选项
    questions_with_options = []
    if use_standard_mbti:
        for q in page_obj:
            option_a = ""
            option_b = ""
            text = q.text
            
            # 解析题目文本，提取A和B选项
            if "A)" in text and "B)" in text:
                # 找到A)和B)的位置
                a_start = text.find("A)")
                b_start = text.find("B)")
                
                if a_start != -1 and b_start != -1:
                    # 提取A选项（A)到B)之间的内容）
                    option_a = text[a_start + 2:b_start].strip()
                    # 提取B选项（B)之后的内容）
                    option_b = text[b_start + 2:].strip()
                    # 题目文本只保留A)之前的部分
                    question_text = text[:a_start].strip()
                    # 去除开头的题目编号（格式：数字. 或 数字.空格）
                    question_text = re.sub(r'^\d+\.\s*', '', question_text)
                else:
                    question_text = text
                    option_a = ""
                    option_b = ""
            else:
                question_text = text
                option_a = ""
                option_b = ""
            
            questions_with_options.append({
                'question': q,
                'question_text': question_text,
                'option_a': option_a,
                'option_b': option_b,
            })
    else:
        # 非标准MBTI，保持原样
        for q in page_obj:
            questions_with_options.append({
                'question': q,
                'question_text': q.text,
                'option_a': '',
                'option_b': '',
            })
    
    return render(request, 'mbti/test.html', {
        "page_obj": page_obj,
        "questions_with_options": questions_with_options,
        "saved_answers": saved_answers,
        "total_questions": questions.count(),
        "current_page": page_obj.number,
        "total_pages": paginator.num_pages,  # 明确传递总页数
        "use_standard_mbti": use_standard_mbti,  # 是否使用标准MBTI格式
    })


@login_required
def save_progress_view(request):
    """保存测试进度的AJAX视图 - 同时保存到session和数据库（重构版）"""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid method'})
    
    try:
        data = json.loads(request.body)
        answers = data.get('answers', {})
        
        if not answers:
            return JsonResponse({'status': 'success', 'saved': 0})
        
        # 保存到session（用于前端显示）
        if not request.session.get('test_answers'):
            request.session['test_answers'] = {}
        request.session['test_answers'].update(answers)
        request.session.modified = True
        
        # 同时保存到数据库（这是最可靠的存储方式）
        qnn = Questionnaire.objects.filter(is_active=True).first()
        if not qnn:
            logger.warning(f"用户 {request.user.username} 保存进度时未找到有效问卷")
            return JsonResponse({'status': 'error', 'message': '未找到有效问卷'})
        
        questions = Question.objects.filter(active=True, questionnaire=qnn)
        valid_question_ids = set(questions.values_list('id', flat=True))
        use_standard = qnn.key == 'mbti_standard_93'
        
        saved_count = 0
        skipped_count = 0
        saved_qids = []
        
        for key, val in answers.items():
            if not key.startswith('q_'):
                continue
                
            try:
                qid = int(key.split('_')[1])
                if qid not in valid_question_ids:
                    skipped_count += 1
                    continue
                
                choice = int(val)
                
                # 验证答案范围
                if use_standard:
                    if not (1 <= choice <= 2):
                        skipped_count += 1
                        logger.warning(f"用户 {request.user.username} 答案 {qid} 的值 {choice} 不在有效范围内 (1-2)")
                        continue
                else:
                    if not (1 <= choice <= 5):
                        skipped_count += 1
                        logger.warning(f"用户 {request.user.username} 答案 {qid} 的值 {choice} 不在有效范围内 (1-5)")
                        continue
                
                # 保存到数据库
                Response.objects.update_or_create(
                    user=request.user,
                    question_id=qid,
                    defaults={"choice": choice, "questionnaire": qnn},
                )
                saved_count += 1
                saved_qids.append(qid)
                
            except (ValueError, IndexError) as e:
                skipped_count += 1
                logger.warning(f"用户 {request.user.username} 解析答案失败: {key}={val}, 错误: {e}")
        
        logger.info(f"用户 {request.user.username} 保存进度: 收到 {len(answers)} 个答案, 数据库保存 {saved_count} 个, 跳过 {skipped_count} 个")
        if saved_qids:
            logger.debug(f"保存的题目ID: {sorted(saved_qids)[:10] if len(saved_qids) > 10 else sorted(saved_qids)}")
        
        return JsonResponse({'status': 'success', 'saved': saved_count})
        
    except Exception as e:
        logger.error(f"用户 {request.user.username} 保存进度失败: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def submit_view(request):
    """提交测试结果 - 完全重构，直接从数据库读取所有答案"""
    if request.method != 'POST':
        return redirect('mbti:test')

    try:
        qnn = Questionnaire.objects.filter(is_active=True).first()
        if not qnn:
            messages.error(request, '未找到有效的问卷，请联系管理员。')
            return redirect('mbti:test')
        
        use_standard = qnn.key == 'mbti_standard_93'
        
        # 获取所有题目ID
        questions = Question.objects.filter(active=True, questionnaire=qnn).order_by('order', 'id')
        valid_question_ids = set(questions.values_list('id', flat=True))
        total_questions = len(valid_question_ids)
        
        logger.info(f"用户 {request.user.username} 提交测试: 需要 {total_questions} 道题")
        
        # 策略：同时从数据库、session和POST收集答案，确保不遗漏
        # 优先级：POST > session > 数据库（POST是最新的）
        answers = {}
        
        # 第一步：从数据库读取所有已保存的答案
        existing_responses = Response.objects.filter(
            user=request.user,
            questionnaire=qnn,
            question_id__in=valid_question_ids
        )
        
        db_count = 0
        for resp in existing_responses:
            if resp.question_id in valid_question_ids:
                # 验证答案范围
                if use_standard:
                    if 1 <= resp.choice <= 2:
                        answers[resp.question_id] = resp.choice
                        db_count += 1
                else:
                    if 1 <= resp.choice <= 5:
                        answers[resp.question_id] = resp.choice
                        db_count += 1
        
        logger.info(f"从数据库读取到 {db_count} 个已保存的答案")
        
        # 第二步：从session补充答案（session会覆盖数据库中的同名答案）
        # 关键：session中可能包含所有页面的答案，必须全部读取并保存到数据库
        session_count = 0
        if hasattr(request, 'session') and 'test_answers' in request.session:
            test_answers = request.session.get('test_answers', {})
            logger.info(f"session中有 {len(test_answers)} 个键值对")
            for key, val in test_answers.items():
                if isinstance(key, str) and key.startswith('q_'):
                    try:
                        qid = int(key.split('_')[1])
                        if qid in valid_question_ids:
                            choice = int(val)
                            # 验证答案范围
                            if use_standard:
                                if 1 <= choice <= 2:
                                    answers[qid] = choice  # session覆盖数据库
                                    session_count += 1
                                    # 立即保存到数据库（确保session中的答案被持久化）
                                    Response.objects.update_or_create(
                                        user=request.user,
                                        question_id=qid,
                                        defaults={"choice": choice, "questionnaire": qnn},
                                    )
                            else:
                                if 1 <= choice <= 5:
                                    answers[qid] = choice  # session覆盖数据库
                                    session_count += 1
                                    # 立即保存到数据库（确保session中的答案被持久化）
                                    Response.objects.update_or_create(
                                        user=request.user,
                                        question_id=qid,
                                        defaults={"choice": choice, "questionnaire": qnn},
                                    )
                    except (ValueError, IndexError) as e:
                        logger.warning(f"解析session答案失败: {key}={val}, 错误: {e}")
                        continue
        
        logger.info(f"从session读取并保存了 {session_count} 个答案到数据库")
        
        # 第三步：用POST中的答案覆盖（POST是用户当前页最新提交的，优先级最高）
        post_count = 0
        for key, val in request.POST.items():
            if key.startswith('q_'):
                try:
                    qid = int(key.split('_')[1])
                    if qid in valid_question_ids:
                        choice = int(val)
                        # 验证答案范围
                        if use_standard:
                            if 1 <= choice <= 2:
                                answers[qid] = choice  # POST覆盖session和数据库
                                post_count += 1
                        else:
                            if 1 <= choice <= 5:
                                answers[qid] = choice  # POST覆盖session和数据库
                                post_count += 1
                except (ValueError, IndexError) as e:
                    logger.warning(f"解析POST答案失败: {key}={val}, 错误: {e}")
                    continue
        
        logger.info(f"从POST获取到 {post_count} 个答案")
        logger.info(f"合并后共有 {len(answers)} 个答案（DB: {db_count}, Session: {session_count}, POST: {post_count}）")
        
        # 第四步：将所有答案保存到数据库（确保数据库有完整备份）
        saved_count = 0
        for qid, choice in answers.items():
            try:
                Response.objects.update_or_create(
                    user=request.user,
                    question_id=qid,
                    defaults={"choice": choice, "questionnaire": qnn},
                )
                saved_count += 1
            except Exception as e:
                logger.error(f"保存答案失败: qid={qid}, choice={choice}, 错误: {e}")
                continue
        
        logger.info(f"已将 {saved_count} 个答案保存到数据库")
        
        # 第三步：检查是否所有题目都已回答
        answered_question_ids = set(answers.keys())
        missing_question_ids = valid_question_ids - answered_question_ids
        missing_count = len(missing_question_ids)
        
        if missing_count > 0:
            logger.warning(f"用户 {request.user.username} 还有 {missing_count} 道题未完成")
            logger.warning(f"缺失题目ID（前10个）: {sorted(list(missing_question_ids))[:10]}")
            logger.warning(f"已完成的题目ID: {sorted(list(answered_question_ids))[:10] if answered_question_ids else '无'}")
            
            # 找到第一个缺失题目的页码，跳转到那一页
            if missing_question_ids:
                first_missing_id = min(missing_question_ids)
                missing_question = questions.filter(id=first_missing_id).first()
                if missing_question:
                    # 根据题目的order计算页码（order从1开始）
                    missing_page = ((missing_question.order - 1) // MBTIScoringService.QUESTIONS_PER_PAGE) + 1
                    logger.info(f"第一个缺失题目ID: {first_missing_id}, order: {missing_question.order}, 页码: {missing_page}")
                    messages.error(request, f'还有 {missing_count} 道题未完成，已自动跳转到第 {missing_page} 页，请继续填写。')
                    # 正确构建URL：先reverse，再添加查询参数
                    redirect_url = reverse('mbti:test')
                    redirect_url += f'?page={missing_page}'
                    return redirect(redirect_url)
            
            messages.error(request, f'还有 {missing_count} 道题未完成，请完成所有题目后再提交。')
            return redirect('mbti:test')

        logger.info(f"用户 {request.user.username} 所有 {total_questions} 道题已完成，开始计算结果")
        
        # 所有答案已保存到数据库（POST中的答案已在第400-419行保存）
        
        if use_standard:
            # 使用标准MBTI 93题计分规则
            # 关键：只计算当前问卷的回答，确保准确性
            responses = Response.objects.filter(
                user=request.user,
                questionnaire=qnn
            ).select_related('question')
            dims_raw, counts = StandardMBTIScoringService.calculate_scores_standard(responses)
            code = StandardMBTIScoringService.generate_type_code_standard(dims_raw)
            
            # 转换为兼容格式（用于存储和显示）
            dims = {}
            confidence = {}
            for dim, scores in dims_raw.items():
                if dim == "IE":
                    dims[dim] = scores["E"] - scores["I"]
                    confidence[dim] = abs(scores["E"] - scores["I"]) / 21.0
                elif dim == "SN":
                    dims[dim] = scores["S"] - scores["N"]
                    confidence[dim] = abs(scores["S"] - scores["N"]) / 26.0
                elif dim == "TF":
                    dims[dim] = scores["T"] - scores["F"]
                    confidence[dim] = abs(scores["T"] - scores["F"]) / 24.0
                elif dim == "JP":
                    dims[dim] = scores["J"] - scores["P"]
                    confidence[dim] = abs(scores["J"] - scores["P"]) / 22.0
        else:
            # 使用原有Likert量表计分规则
            responses = Response.objects.filter(user=request.user).select_related('question')
            dims, counts = MBTIScoringService.calculate_scores(responses)
            code = MBTIScoringService.generate_type_code(dims)
            confidence = MBTIScoringService.calculate_confidence(dims, counts)

        # 保存结果
        try:
            result, created = Result.objects.update_or_create(
                user=request.user,
                defaults={
                    "type_code": code,
                    "score_detail": dims,
                    "confidence": confidence,
                    "questionnaire": qnn
                },
            )
            logger.info(f"用户 {request.user.username} 测试结果已保存: {code}, created={created}")
        except Exception as e:
            logger.error(f"保存测试结果失败: {e}", exc_info=True)
            raise

        # 清除session中的答案（在保存结果后清除，避免重复提交）
        if hasattr(request, 'session') and 'test_answers' in request.session:
            del request.session['test_answers']
            request.session.modified = True
        
        logger.info(f"用户 {request.user.username} 完成MBTI测试，结果: {code}，重定向到结果页")
        messages.success(request, '提交成功，以下是你的测试结果')
        return redirect('mbti:result')
        
    except Exception as e:
        logger.error(f"处理用户 {request.user.username} 的MBTI测试提交时出错: {e}", exc_info=True)
        messages.error(request, f'提交失败：{str(e)}。请稍后重试。如问题持续，请联系管理员。')
        return redirect('mbti:test')


@login_required
def result_view(request):
    """显示测试结果视图"""
    result = Result.objects.filter(user=request.user).order_by('-created_at').first()
    if not result:
        messages.warning(request, '您还没有测试结果，请先完成测试')
        return redirect('mbti:test')
    
    score_items = list(result.score_detail.items())
    confidence = result.confidence
    detail_items = [(k, v, confidence.get(k)) for (k, v) in score_items]
    profile = TypeProfile.objects.filter(code=result.type_code).first()
    
    return render(request, 'mbti/result.html', {
        "result": result,
        "detail_items": detail_items,
        "profile": profile
    })


@login_required
def result_pdf_view(request):
    """生成并返回PDF测试报告"""
    result = Result.objects.filter(user=request.user).order_by('-created_at').first()
    if not result:
        messages.warning(request, '您还没有测试结果，请先完成测试')
        return redirect('mbti:test')

    # 延迟导入报告库，给出友好降级
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.lib.units import inch
    except ImportError:
        messages.error(request, 'PDF导出模块未安装，请稍后重试或联系管理员安装 reportlab')
        return redirect('mbti:result')

    # 注册中文字体，避免乱码（跨平台）
    base_font = 'Helvetica'
    try:
        import os
        import sys
        # 常见平台字体路径（包含 Windows、Linux(Ubuntu) 与 macOS）
        font_paths = [
            # Windows
            r'C:\Windows\Fonts\msyh.ttf',  # 微软雅黑 (TTF)
            r'C:\Windows\Fonts\msyh.ttc',  # 微软雅黑 (TTC)
            r'C:\Windows\Fonts\simhei.ttf',  # 黑体
            r'C:\Windows\Fonts\simsun.ttc',  # 宋体（可能不被TTFont识别）
            r'C:\Windows\Fonts\simsun.ttf',  # 宋体 (TTF)
            r'C:\Windows\Fonts\NSimSun.ttf',  # 新宋体
            r'C:\Windows\Fonts\SIMKAI.TTF',  # 楷体
        ]

        # Linux 常见中文字体（优先使用 Noto/思源系列，ReportLab 对 OTF/TTF支持更稳定）
        linux_candidates = [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf',
            '/usr/share/fonts/noto-cjk/NotoSansCJKsc-Regular.otf',
            '/usr/share/fonts/noto/NotoSansCJKsc-Regular.otf',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
            '/usr/share/fonts/truetype/arphic/ukai.ttf',
            '/usr/share/fonts/truetype/arphic/uming.ttf',
        ]

        # macOS 常见中文字体
        mac_candidates = [
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STSong.ttf',
            '/Library/Fonts/Songti.ttc',
            '/Library/Fonts/Heiti.ttc',
        ]

        if sys.platform.startswith('linux'):
            font_paths.extend(linux_candidates)
        elif sys.platform == 'darwin':
            font_paths.extend(mac_candidates)

        # 项目内置字体（如存在）：static/fonts/NotoSansCJKsc-Regular.otf
        BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_font = os.path.join(BASE_DIR, 'static', 'fonts', 'NotoSansCJKsc-Regular.otf')
        font_paths.append(project_font)

        for font_path in font_paths:
            try:
                if os.path.exists(font_path):
                    pdfmetrics.registerFont(TTFont('CN', font_path))
                    base_font = 'CN'
                    break
            except Exception:
                # 某些 .ttc 字体包不被 TTFont 支持，继续尝试下一个
                continue
        # 若仍未找到可用 TTF/TTC，尝试使用内置的 CJK 字体（不需外部文件）
        if base_font == 'Helvetica':
            try:
                pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
                base_font = 'STSong-Light'
            except Exception:
                pass
    except Exception:
        # 字体注册失败时退回默认英文字体（中文可能出现方块）
        pass

    # 样式 - 优化字体大小和间距
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=base_font,
        fontSize=24,
        spaceAfter=20,
        spaceBefore=10,
        alignment=1,  # 居中
        textColor=colors.HexColor('#1a237e'),  # 深蓝色
        leading=28
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=base_font,
        fontSize=16,
        spaceAfter=10,
        spaceBefore=15,
        textColor=colors.HexColor('#283593'),  # 深蓝色
        backColor=colors.HexColor('#e8eaf6'),  # 浅蓝色背景
        borderWidth=0,
        borderPadding=8,
        leading=20
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=11,
        spaceAfter=10,
        leftIndent=0,
        rightIndent=0,
        leading=16,  # 行距
        textColor=colors.black
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=10,
        spaceAfter=6,
        leftIndent=10,
        leading=14
    )

    # 类型档案 - 确保正确查询
    profile = TypeProfile.objects.filter(code=result.type_code.upper()).first()
    if not profile:
        # 如果找不到，尝试不区分大小写
        profile = TypeProfile.objects.filter(code__iexact=result.type_code).first()
    
    strengths = getattr(profile, 'strengths', '') or '—' if profile else '—'
    growth = getattr(profile, 'growth', '') or '—' if profile else '—'
    description = getattr(profile, 'description', '') or '—' if profile else '—'
    profile_name = getattr(profile, 'name', '未知类型') if profile else '未知类型'

    # 构建文档 - 使用A4页面，优化边距
    from io import BytesIO
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,  # 使用A4而不是letter
        topMargin=72,  # 约2.5cm
        bottomMargin=72,
        leftMargin=72,
        rightMargin=72,
        title='MBTI人格测试报告'
    )
    story = []
    
    # 添加标题
    story.append(Paragraph('MBTI人格测试报告', title_style))
    story.append(Spacer(1, 30))
    
    # 基本信息表格
    story.append(Paragraph('基本信息', heading_style))
    basic_data = [
        ['用户名', request.user.username],
        ['测试时间', result.created_at.strftime('%Y年%m月%d日 %H:%M') if hasattr(result, 'created_at') else '—'],
        ['人格类型', f"{result.type_code} - {profile_name}"],
        ['测试题目数', Response.objects.filter(user=request.user).count()]
    ]
    
    basic_table = Table(basic_data, colWidths=[2*inch, 4.5*inch])
    basic_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e3f2fd')),  # 浅蓝色背景
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),  # 第一列左对齐
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),  # 第二列左对齐
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),  # 垂直居中
        ('FONTNAME', (0, 0), (-1, -1), base_font),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#90caf9')),  # 蓝色边框
        ('FONTNAME', (0, 0), (0, -1), base_font),  # 确保使用中文字体
        ('FONTNAME', (1, 0), (1, -1), base_font),
    ]))
    story.append(basic_table)
    story.append(Spacer(1, 20))
    
    # 类型描述
    story.append(Paragraph('性格概述', heading_style))
    story.append(Paragraph(description, normal_style))
    story.append(Spacer(1, 20))
    
    # 维度分析表格
    story.append(Paragraph('维度分析', heading_style))
    
    # 修复维度显示逻辑
    def get_dimension_label(dim_code, score):
        """根据维度代码和分数返回正确的标签"""
        if dim_code == 'IE':
            return '外向' if score > 0 else '内向'
        elif dim_code == 'SN':
            return '感觉' if score > 0 else '直觉'
        elif dim_code == 'TF':
            return '思考' if score > 0 else '情感'
        elif dim_code == 'JP':
            return '判断' if score > 0 else '知觉'
        return '未知'
    
    dimension_data = [['维度', '分数', '置信度', '倾向']] + [
        [
            k, 
            f"{v:+.2f}", 
            f"{result.confidence.get(k, 0):.2f}",
            get_dimension_label(k, v)
        ] for k, v in result.score_detail.items()
    ]
    
    dimension_table = Table(dimension_data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.8*inch])
    dimension_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976d2')),  # 蓝色表头
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 0), (-1, -1), base_font),
        ('FONTSIZE', (0, 0), (-1, 0), 12),  # 表头字体稍大
        ('FONTSIZE', (0, 1), (-1, -1), 11),  # 数据行字体
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f5f5f5')),  # 浅灰色背景
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#bdbdbd')),  # 灰色边框
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fafafa')])  # 交替行背景
    ]))
    story.append(dimension_table)
    story.append(Spacer(1, 20))
    
    # 多维度深度分析
    story.append(Paragraph('多维度深度分析', heading_style))
    
    analysis_sections = [
        ('性格特点', getattr(profile, 'personality_traits', '') if profile else ''),
        ('工作风格', getattr(profile, 'work_style', '') if profile else ''),
        ('人际关系', getattr(profile, 'interpersonal_relations', '') if profile else ''),
        ('情感表达', getattr(profile, 'emotional_expression', '') if profile else ''),
        ('决策方式', getattr(profile, 'decision_making', '') if profile else ''),
        ('压力管理', getattr(profile, 'stress_management', '') if profile else ''),
        ('学习方式', getattr(profile, 'learning_style', '') if profile else ''),
        ('职业建议', getattr(profile, 'career_suggestions', '') if profile else ''),
        ('生活哲学', getattr(profile, 'life_philosophy', '') if profile else ''),
        ('沟通风格', getattr(profile, 'communication_style', '') if profile else '')
    ]
    
    for section_title, content in analysis_sections:
        if content:  # 只显示有内容的部分
            # 使用更好的段落样式
            section_title_style = ParagraphStyle(
                'SectionTitle',
                parent=normal_style,
                fontSize=13,
                textColor=colors.HexColor('#1565c0'),
                spaceAfter=8,
                spaceBefore=5,
                leftIndent=0,
                fontName=base_font,
                leading=18
            )
            story.append(Paragraph(f"<b>{section_title}</b>", section_title_style))
            
            # 内容样式，优化行距和缩进
            content_style = ParagraphStyle(
                'SectionContent',
                parent=normal_style,
                fontSize=11,
                spaceAfter=12,
                leftIndent=20,
                rightIndent=0,
                leading=17,
                fontName=base_font
            )
            story.append(Paragraph(content, content_style))
    
    # 详细维度分析
    story.append(Paragraph('维度详细分析', heading_style))
    
    # 为每个维度提供详细解释
    dimension_explanations = {
        'IE': {
            'name': '外向性 vs 内向性',
            'description': '这个维度反映了你获取能量的方式和注意力的方向。',
            'I': '内向型：从内部世界获取能量，喜欢独处思考，更关注内心世界。',
            'E': '外向型：从外部世界获取能量，喜欢与人交往，思考时倾向于外化表达。'
        },
        'SN': {
            'name': '感觉 vs 直觉',
            'description': '这个维度反映了你收集和处理信息的偏好方式。',
            'S': '感觉型：关注具体事实和细节，相信经验和实际观察，注重现实。',
            'N': '直觉型：关注可能性和模式，相信灵感和想象，注重未来潜力。'
        },
        'TF': {
            'name': '思考 vs 情感',
            'description': '这个维度反映了你做决策时的主要考虑因素。',
            'T': '思考型：基于逻辑分析做决策，重视客观标准和公平原则。',
            'F': '情感型：基于价值观和人际关系做决策，重视和谐与个人价值。'
        },
        'JP': {
            'name': '判断 vs 知觉',
            'description': '这个维度反映了你对外部世界的态度和生活方式偏好。',
            'J': '判断型：喜欢有计划和结构的生活，倾向于做决定和完成任务。',
            'P': '知觉型：喜欢灵活和开放的生活，倾向于保持选择余地和适应变化。'
        }
    }
    
    for dim_code, score in result.score_detail.items():
        if dim_code in dimension_explanations:
            dim_info = dimension_explanations[dim_code]
            confidence = result.confidence.get(dim_code, 0)
            
            # 维度标题
            story.append(Paragraph(f"{dim_info['name']} ({dim_code})", ParagraphStyle(
                'DimensionTitle',
                parent=normal_style,
                fontSize=13,
                textColor=colors.darkred,
                spaceAfter=8,
                spaceBefore=15,
                fontName=base_font,
                bold=True
            )))
            
            # 维度描述
            story.append(Paragraph(dim_info['description'], normal_style))
            
            # 分数与倾向：根据实际计算逻辑确定维度倾向
            # dims["SN"] = S_score - N_score，所以正数=S，负数=N
            # dims["TF"] = T_score - F_score，所以正数=T，负数=F
            # dims["JP"] = J_score - P_score，所以正数=J，负数=P
            # dims["IE"] = E_score - I_score，所以正数=E，负数=I
            if dim_code == 'SN':
                chosen_letter = 'S' if score > 0 else 'N'
            elif dim_code == 'TF':
                chosen_letter = 'T' if score > 0 else 'F'
            elif dim_code == 'JP':
                chosen_letter = 'J' if score > 0 else 'P'
            else:  # IE
                chosen_letter = 'E' if score > 0 else 'I'
            
            tendency = dim_info.get(chosen_letter, '')
            score_text = f"您的分数：{score:+.2f}，置信度：{confidence:.2f}"
            
            story.append(Paragraph(f"<b>{score_text}</b>", ParagraphStyle(
                'ScoreText',
                parent=normal_style,
                fontSize=12,
                textColor=colors.HexColor('#2e7d32'),  # 深绿色
                spaceAfter=8,
                leftIndent=0,
                fontName=base_font,
                leading=16
            )))
            
            story.append(Paragraph(tendency, ParagraphStyle(
                'TendencyText',
                parent=normal_style,
                fontSize=11,
                leftIndent=15,
                rightIndent=0,
                spaceAfter=12,
                fontName=base_font,
                backColor=colors.HexColor('#f5f5f5'),
                borderWidth=0,
                borderPadding=10,
                leading=16
            )))
    
    # 综合分析
    story.append(Paragraph('综合人格分析', heading_style))
    
    # 计算整体倾向强度
    total_strength = sum(abs(score) for score in result.score_detail.values()) / len(result.score_detail) if result.score_detail else 0
    avg_confidence = sum(result.confidence.values()) / len(result.confidence) if result.confidence and len(result.confidence) > 0 else 0
    
    # 构建综合分析内容
    overall_parts = []
    overall_parts.append(f"根据您的测试结果，您的人格类型为 <b>{result.type_code}</b>")
    if profile_name and profile_name != '未知类型':
        overall_parts.append(f"（{profile_name}）")
    
    overall_parts.append("")
    overall_parts.append(f"<b>整体特征强度：</b>{total_strength:.2f}（范围0-4，数值越高表示特征越明显）")
    overall_parts.append(f"<b>平均置信度：</b>{avg_confidence:.2f}（范围0-1，数值越高表示结果越可靠）")
    overall_parts.append("")
    
    # 根据强度给出评价
    if total_strength > 3:
        strength_desc = "非常明显"
    elif total_strength > 2:
        strength_desc = "较为明显"
    elif total_strength > 1:
        strength_desc = "相对温和"
    else:
        strength_desc = "较为平衡"
    
    if avg_confidence > 0.7:
        confidence_desc = "较高"
    elif avg_confidence > 0.5:
        confidence_desc = "中等"
    else:
        confidence_desc = "需要进一步验证"
    
    overall_parts.append(f"这意味着您在各个维度上的倾向性{strength_desc}，测试结果的可靠性{confidence_desc}。")
    
    # 添加类型描述
    if description and description != '—':
        overall_parts.append("")
        overall_parts.append(f"<b>类型概述：</b>{description}")
    
    overall_analysis = "<br/>".join(overall_parts)
    
    story.append(Paragraph(overall_analysis, normal_style))
    story.append(Spacer(1, 15))
    
    # 发展建议增强版
    story.append(Paragraph('个人发展建议', heading_style))
    
    # 基于分数提供个性化建议
    development_suggestions = []
    
    # 为每个维度提供详细建议
    dimension_suggestions = {
        'IE': {
            'high': "您在内外向维度上表现出明显的倾向。建议充分利用您的能量获取方式，同时适当发展对侧能力，以增强适应性。",
            'low': "您在内外向维度上较为平衡。建议在不同情境下尝试不同的行为模式，找到最适合的能量获取方式，既能享受独处的思考时光，也能在社交中获得能量。"
        },
        'SN': {
            'high': "您在感觉-直觉维度上表现出明显的倾向。建议在保持优势的同时，适当关注对侧能力，以更全面地处理信息。",
            'low': "您在感觉-直觉维度上展现出灵活性。建议培养既关注细节又把握大局的能力，既能处理具体事实，也能看到未来可能性。"
        },
        'TF': {
            'high': "您在思考-情感维度上表现出明显的倾向。建议在决策时适当考虑对侧因素，使决策更加全面和平衡。",
            'low': "您在思考-情感维度上能够平衡理性和感性。建议在决策时综合考虑逻辑分析和人际影响，既能做出客观判断，也能顾及他人感受。"
        },
        'JP': {
            'high': "您在判断-知觉维度上表现出明显的倾向。建议在保持优势的同时，适当发展对侧能力，以增强生活和工作中的灵活性。",
            'low': "您在判断-知觉维度上具有适应性。建议根据情况需要，灵活运用计划性和开放性，既能按计划执行，也能适应变化。"
        }
    }
    
    for dim_code, score in result.score_detail.items():
        confidence = result.confidence.get(dim_code, 0)
        abs_score = abs(score)
        
        # 根据分数绝对值判断倾向强度
        if abs_score > 3:
            suggestion_type = 'high'
        else:
            suggestion_type = 'low'
        
        if dim_code in dimension_suggestions:
            suggestion = dimension_suggestions[dim_code][suggestion_type]
            development_suggestions.append(suggestion)
    
    if development_suggestions:
        story.append(Paragraph("<b>基于维度分析的发展建议：</b>", ParagraphStyle(
            'SuggestionTitle',
            parent=normal_style,
            fontSize=11,
            spaceAfter=8,
            fontName=base_font
        )))
        for i, suggestion in enumerate(development_suggestions, 1):
            story.append(Paragraph(f"{i}. {suggestion}", ParagraphStyle(
                'SuggestionText',
                parent=normal_style,
                leftIndent=30,
                rightIndent=20,
                spaceAfter=8,
                fontName=base_font
            )))
        story.append(Spacer(1, 10))
    
    # 类型特定的发展建议
    if growth and growth != '—':
        story.append(Paragraph("<b>针对您的人格类型的发展建议：</b>", ParagraphStyle(
            'SuggestionTitle',
            parent=normal_style,
            fontSize=11,
            spaceAfter=8,
            fontName=base_font
        )))
        story.append(Paragraph(growth, normal_style))
        story.append(Spacer(1, 10))
    
    # 添加优势说明
    if strengths and strengths != '—':
        story.append(Paragraph("<b>您的性格优势：</b>", ParagraphStyle(
            'SuggestionTitle',
            parent=normal_style,
            fontSize=11,
            spaceAfter=8,
            fontName=base_font
        )))
        story.append(Paragraph(strengths, normal_style))
        story.append(Spacer(1, 10))
    
    # 职业发展建议
    if profile and hasattr(profile, 'career_suggestions') and profile.career_suggestions:
        story.append(Paragraph("<b>职业发展建议：</b>", ParagraphStyle(
            'SuggestionTitle',
            parent=normal_style,
            fontSize=11,
            spaceAfter=8,
            fontName=base_font
        )))
        story.append(Paragraph(profile.career_suggestions, normal_style))
    
    story.append(Spacer(1, 20))

    # 页脚信息
    story.append(Spacer(1, 30))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontName=base_font,
        fontSize=8,
        alignment=1,
        textColor=colors.grey
    )
    story.append(Paragraph('本报告由MBTI人格测试系统生成', footer_style))
    story.append(Paragraph(f"生成时间：{result.created_at.strftime('%Y年%m月%d日 %H:%M:%S') if hasattr(result, 'created_at') else '—'}", footer_style))

    doc.build(story)
    buffer.seek(0)

    from django.http import HttpResponse
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="MBTI测试报告_{request.user.username}_{result.created_at.strftime("%Y%m%d") if hasattr(result, "created_at") else "report"}.pdf"'
    return response