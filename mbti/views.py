from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
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
    # 检查用户是否有测试结果
    has_result = False
    latest_result = None
    if request.user.is_authenticated:
        latest_result = Result.objects.filter(user=request.user).order_by('-created_at').first()
        has_result = latest_result is not None
    
    # 首页卡片的图标和兜底短描述；类型名称与详细描述优先从数据库 TypeProfile 读取。
    type_base = [
        {'icon': '🧠', 'title': '研究战略架构师', 'code': 'INTJ', 'desc': '擅长长期路线设计和复杂问题系统化拆解'},
        {'icon': '🔬', 'title': '理论机制探索者', 'code': 'INTP', 'desc': '擅长追问模型机制、逻辑边界和异常现象'},
        {'icon': '🧭', 'title': '科研项目指挥官', 'code': 'ENTJ', 'desc': '擅长组织多人协作并推动项目向成果收束'},
        {'icon': '🎤', 'title': '前沿想法孵化者', 'code': 'ENTP', 'desc': '擅长提出新角度、连接领域并挑战假设'},
        {'icon': '🛡️', 'title': '愿景整合型导师', 'code': 'INFJ', 'desc': '擅长连接研究意义、团队成长和长期方向'},
        {'icon': '🎭', 'title': '使命驱动探索者', 'code': 'INFP', 'desc': '擅长发现有价值感和社会意义的深层问题'},
        {'icon': '🎯', 'title': '团队培养型领导者', 'code': 'ENFJ', 'desc': '擅长激励成员、建立共识并促进团队成长'},
        {'icon': '🌟', 'title': '跨界创意连接者', 'code': 'ENFP', 'desc': '擅长连接人、场景和跨学科研究机会'},
        {'icon': '📋', 'title': '实验流程守护者', 'code': 'ISTJ', 'desc': '擅长维护实验复现性、文档和质量标准'},
        {'icon': '🛡️', 'title': '研究支持协调者', 'code': 'ISFJ', 'desc': '擅长稳定支持团队运行和具体协作细节'},
        {'icon': '📊', 'title': '项目交付负责人', 'code': 'ESTJ', 'desc': '擅长任务拆解、进度管理和项目落地'},
        {'icon': '🤝', 'title': '实验室协作组织者', 'code': 'ESFJ', 'desc': '擅长维护协作秩序和团队日常连接'},
        {'icon': '🔧', 'title': '系统调试攻坚者', 'code': 'ISTP', 'desc': '擅长定位训练、环境和系统中的技术问题'},
        {'icon': '🎨', 'title': '体验敏感型原型师', 'code': 'ISFP', 'desc': '擅长发现原型、体验和结果呈现中的细节问题'},
        {'icon': '⚡', 'title': '快速试验攻坚者', 'code': 'ESTP', 'desc': '擅长短周期验证、demo攻关和高压应变'},
        {'icon': '🎭', 'title': '科研传播激活者', 'code': 'ESFP', 'desc': '擅长成果展示、现场互动和研究传播'},
    ]
    
    # 从数据库获取详细的类型档案信息
    type_list = []
    for item in type_base:
        profile = TypeProfile.objects.filter(code__iexact=item['code']).first()
        profile_desc = profile.description if profile else ''
        short_desc = item['desc']
        if profile_desc:
            first_sentence = profile_desc.split('。', 1)[0].strip()
            short_desc = f"{first_sentence}。" if first_sentence else item['desc']
        type_data = {
            'icon': item['icon'],
            'title': profile.name if profile and profile.name else item['title'],
            'code': item['code'],
            'desc': short_desc,
            'description': profile_desc or item['desc'],
            'strengths': profile.strengths if profile else '',
            'growth': profile.growth if profile else '',
            'career_suggestions': profile.career_suggestions if profile else '',
            'work_style': profile.work_style if profile else '',
            'interpersonal_relations': profile.interpersonal_relations if profile else '',
        }
        type_list.append(type_data)
    
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
    
    # 如果是重新测试，清除之前的答案和session
    if retake:
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
    
    # 分页处理
    page_number = request.GET.get('page', 1)
    paginator = Paginator(questions, MBTIScoringService.QUESTIONS_PER_PAGE)
    
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        # 如果页码不是整数，显示第一页
        page_obj = paginator.page(1)
    except EmptyPage:
        # 如果页码超出范围，显示最后一页
        page_obj = paginator.page(paginator.num_pages)
    
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
    """保存测试进度的AJAX视图 - 同时保存到session和数据库"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            answers = data.get('answers', {})
            
            # 保存到session
            if not request.session.get('test_answers'):
                request.session['test_answers'] = {}
            request.session['test_answers'].update(answers)
            request.session.modified = True
            
            # 同时保存到数据库（确保即使session丢失，数据库也有备份）
            qnn = Questionnaire.objects.filter(is_active=True).first()
            if qnn:
                questions = Question.objects.filter(active=True, questionnaire=qnn)
                valid_question_ids = set(questions.values_list('id', flat=True))
                
                saved_count = 0
                skipped_count = 0
                for key, val in answers.items():
                    if key.startswith('q_'):
                        try:
                            qid = int(key.split('_')[1])
                            if qid in valid_question_ids:
                                choice = int(val)
                                # 验证答案范围
                                use_standard = qnn and qnn.key == 'mbti_standard_93'
                                if use_standard:
                                    if 1 <= choice <= 2:
                                        Response.objects.update_or_create(
                                            user=request.user,
                                            question_id=qid,
                                            defaults={"choice": choice, "questionnaire": qnn},
                                        )
                                        saved_count += 1
                                    else:
                                        skipped_count += 1
                                        logger.warning(f"答案 {qid} 的值 {choice} 不在有效范围内 (1-2)")
                                else:
                                    if 1 <= choice <= 5:
                                        Response.objects.update_or_create(
                                            user=request.user,
                                            question_id=qid,
                                            defaults={"choice": choice, "questionnaire": qnn},
                                        )
                                        saved_count += 1
                                    else:
                                        skipped_count += 1
                            else:
                                skipped_count += 1
                                logger.debug(f"题目ID {qid} 不属于当前问卷 (valid IDs: {sorted(list(valid_question_ids))[:5]}...)")
                        except (ValueError, IndexError) as e:
                            skipped_count += 1
                            logger.warning(f"解析答案失败: {key}={val}, 错误: {e}")
                
                logger.info(f"用户 {request.user.username} 保存进度: session {len(answers)} 个答案, 数据库保存 {saved_count} 个, 跳过 {skipped_count} 个")
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            logger.error(f"保存进度失败: {e}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid method'})


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
        
        # 策略：直接从数据库读取所有已保存的Response（这是唯一可靠来源）
        # 然后用POST中的答案覆盖（因为POST是用户当前页最新提交的）
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
        
        # 第二步：用POST中的答案覆盖（用户当前页最新提交的）
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
                                answers[qid] = choice
                                post_count += 1
                                # 立即保存到数据库
                                Response.objects.update_or_create(
                                    user=request.user,
                                    question_id=qid,
                                    defaults={"choice": choice, "questionnaire": qnn},
                                )
                        else:
                            if 1 <= choice <= 5:
                                answers[qid] = choice
                                post_count += 1
                                # 立即保存到数据库
                                Response.objects.update_or_create(
                                    user=request.user,
                                    question_id=qid,
                                    defaults={"choice": choice, "questionnaire": qnn},
                                )
                except (ValueError, IndexError) as e:
                    logger.warning(f"解析POST答案失败: {key}={val}, 错误: {e}")
                    continue
        
        logger.info(f"从POST获取到 {post_count} 个答案，已保存到数据库")
        logger.info(f"合并后共有 {len(answers)} 个答案")
        
        # 第三步：检查是否所有题目都已回答
        answered_question_ids = set(answers.keys())
        missing_question_ids = valid_question_ids - answered_question_ids
        missing_count = len(missing_question_ids)
        
        if missing_count > 0:
            logger.warning(f"用户 {request.user.username} 还有 {missing_count} 道题未完成")
            logger.warning(f"缺失题目ID（前10个）: {sorted(list(missing_question_ids))[:10]}")
            messages.error(request, f'还有 {missing_count} 道题未完成，请完成所有题目后再提交。')
            return redirect('mbti:test')

        logger.info(f"用户 {request.user.username} 所有 {total_questions} 道题已完成，开始计算结果")
        
        # 注意：所有答案已经在上面保存到数据库了（POST中的答案在第324-338行已保存）
        # 数据库中的答案已经在第289-306行读取了
        
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
        
        logger.info(f"User {request.user.username} completed MBTI test, result: {code}, redirecting to result page")
        messages.success(request, '提交成功，以下是你的 MBTI-Research 测评结果')
        return redirect('mbti:result')
        
    except Exception as e:
        logger.error(f"Error processing MBTI test submission for user {request.user.username}: {e}", exc_info=True)
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        messages.error(request, f'提交失败：{str(e)}。请稍后重试。如问题持续，请联系管理员。')
        return redirect('mbti:test')


@login_required
def result_view(request):
    # 获取用户最新的测试结果（按创建时间倒序）
    result = Result.objects.filter(user=request.user).order_by('-created_at').first()
    score_items = list(result.score_detail.items()) if result else []
    confidence = result.confidence if result else {}
    detail_items = [(k, v, confidence.get(k)) for (k, v) in score_items]
    profile = TypeProfile.objects.filter(code=result.type_code).first() if result else None
    return render(request, 'mbti/result.html', {"result": result, "detail_items": detail_items, "profile": profile})


@login_required
def result_pdf_view(request):
    """生成完整详细的PDF测试报告"""
    from django.utils import timezone
    
    result = Result.objects.filter(user=request.user).first()
    if not result:
        return redirect('mbti:test')

    # 延迟导入报告库
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        from reportlab.lib.units import inch, cm
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except Exception:
        messages.error(request, 'PDF导出模块未安装，请稍后重试或联系管理员安装 reportlab')
        return redirect('mbti:result')

    # 注册中文字体
    base_font = 'Helvetica'
    try:
        import os, sys
        font_paths = [
            r'C:\Windows\Fonts\msyh.ttf',
            r'C:\Windows\Fonts\simhei.ttf',
            '/System/Library/Fonts/PingFang.ttc',
            '/System/Library/Fonts/STSong.ttf',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        ]
        
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
                continue
        
        if base_font == 'Helvetica':
            try:
                pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
                base_font = 'STSong-Light'
            except Exception:
                pass
    except Exception:
        pass

    # 获取类型档案
    profile = TypeProfile.objects.filter(code__iexact=result.type_code).first()
    profile_name = getattr(profile, 'name', '') if profile else ''
    description = getattr(profile, 'description', '') if profile else ''
    strengths = getattr(profile, 'strengths', '') if profile else ''
    growth = getattr(profile, 'growth', '') if profile else ''

    # 关键修复：使用 localtime 转换为北京时间
    test_time_raw = result.updated_at if hasattr(result, 'updated_at') and result.updated_at else result.created_at
    test_time = timezone.localtime(test_time_raw)  # 转换为本地时间（北京时间）
    now_local = timezone.localtime(timezone.now())  # 当前时间也转换

    # 定义样式
    styles = getSampleStyleSheet()
    
    # 主标题样式
    title_style = ParagraphStyle(
        'Title', fontName=base_font, fontSize=24, alignment=TA_CENTER,
        textColor=colors.HexColor('#1e3a5f'), spaceAfter=20, spaceBefore=10
    )
    
    # 副标题样式
    subtitle_style = ParagraphStyle(
        'Subtitle', fontName=base_font, fontSize=14, alignment=TA_CENTER,
        textColor=colors.HexColor('#666666'), spaceAfter=30
    )
    
    # 章节标题样式
    section_style = ParagraphStyle(
        'Section', fontName=base_font, fontSize=14, 
        textColor=colors.HexColor('#1e3a5f'), spaceBefore=20, spaceAfter=10,
        borderWidth=0, borderPadding=0, leftIndent=0
    )
    
    # 正文样式
    body_style = ParagraphStyle(
        'Body', fontName=base_font, fontSize=10, 
        textColor=colors.HexColor('#333333'), spaceAfter=8, leading=16,
        leftIndent=0, rightIndent=0
    )
    
    # 小节标题样式
    subsection_style = ParagraphStyle(
        'Subsection', fontName=base_font, fontSize=11,
        textColor=colors.HexColor('#1e3a5f'), spaceBefore=12, spaceAfter=6,
        leftIndent=10
    )

    # 列表项样式
    list_style = ParagraphStyle(
        'List', fontName=base_font, fontSize=10,
        textColor=colors.HexColor('#444444'), spaceAfter=4, leading=14,
        leftIndent=20, rightIndent=10
    )
    
    # 页脚样式
    footer_style = ParagraphStyle(
        'Footer', fontName=base_font, fontSize=8, alignment=TA_CENTER,
        textColor=colors.HexColor('#999999')
    )

    # 构建文档
    from io import BytesIO
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, 
        topMargin=2*cm, bottomMargin=2*cm, 
        leftMargin=2*cm, rightMargin=2*cm,
        title='MBTI-Research科研协作测评报告'
    )
    story = []
    
    # ==================== 第一页：封面 ====================
    story.append(Spacer(1, 3*cm))
    story.append(Paragraph('MBTI-Research 科研协作测评报告', title_style))
    story.append(Spacer(1, 1*cm))
    
    # 大号类型码
    type_code_style = ParagraphStyle(
        'TypeCode', fontName=base_font, fontSize=48, alignment=TA_CENTER,
        textColor=colors.HexColor('#667eea'), spaceAfter=10
    )
    story.append(Paragraph(f'<b>{result.type_code}</b>', type_code_style))
    
    if profile_name:
        story.append(Paragraph(profile_name, subtitle_style))
    
    story.append(Spacer(1, 2*cm))
    
    # 基本信息表格 - 使用转换后的北京时间
    info_data = [
        ['用户', request.user.username],
        ['测试时间', test_time.strftime('%Y年%m月%d日 %H:%M')],
        ['题目数量', '93题'],
    ]
    
    info_table = Table(info_data, colWidths=[3*cm, 6*cm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), base_font),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#666666')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#333333')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(info_table)
    
    story.append(PageBreak())
    
    # ==================== 第二页：科研画像概述 ====================
    story.append(Paragraph('◆ 科研画像概述', section_style))
    story.append(Spacer(1, 0.3*cm))
    
    if description:
        story.append(Paragraph(description, body_style))
    else:
        story.append(Paragraph('暂无详细描述。', body_style))
    
    story.append(Spacer(1, 0.5*cm))
    
    # ==================== 维度分析 ====================
    story.append(Paragraph('◆ 四维度分析', section_style))
    story.append(Spacer(1, 0.3*cm))
    
    # 维度解释
    dim_labels = {
        'IE': ('内向 (I)', '外向 (E)', '能量来源'),
        'SN': ('感觉 (S)', '直觉 (N)', '信息获取'),
        'TF': ('思考 (T)', '情感 (F)', '决策方式'),
        'JP': ('判断 (J)', '知觉 (P)', '生活态度'),
    }
    
    dim_data = [['维度', '倾向', '分数', '置信度']]
    for k, v in result.score_detail.items():
        if k in dim_labels:
            left, right, name = dim_labels[k]
            conf = result.confidence.get(k, 0)
            # 修正倾向判断逻辑
            if k == 'IE':
                tendency = '外向' if v > 0 else '内向'
            elif k == 'SN':
                tendency = '感觉' if v > 0 else '直觉'
            elif k == 'TF':
                tendency = '思考' if v > 0 else '情感'
            else:
                tendency = '判断' if v > 0 else '知觉'
            dim_data.append([name, tendency, f'{v:+.1f}', f'{conf:.0%}'])
    
    dim_table = Table(dim_data, colWidths=[4*cm, 3*cm, 3*cm, 3*cm])
    dim_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), base_font),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f8f9fa'), colors.white]),
    ]))
    story.append(dim_table)
    
    story.append(Spacer(1, 0.5*cm))
    
    # 详细维度解释
    dim_explanations = {
        'IE': {
            'name': '能量来源维度 (E-I)',
            'E': '外向型 (E)：从与他人互动中获取能量，喜欢社交活动，思考时倾向于边说边想。',
            'I': '内向型 (I)：从独处和内省中获取能量，享受深度思考，更喜欢书面沟通。'
        },
        'SN': {
            'name': '信息获取维度 (S-N)',
            'S': '感觉型 (S)：关注具体事实和细节，相信经验和实际数据，脚踏实地。',
            'N': '直觉型 (N)：关注整体模式和可能性，富有想象力，喜欢探索新概念。'
        },
        'TF': {
            'name': '决策方式维度 (T-F)',
            'T': '思考型 (T)：决策时重视逻辑分析，追求客观公正，关注效率。',
            'F': '情感型 (F)：决策时考虑人际和谐，重视他人感受，追求共识。'
        },
        'JP': {
            'name': '生活态度维度 (J-P)',
            'J': '判断型 (J)：喜欢有计划有组织的生活，做事果断，追求确定性。',
            'P': '知觉型 (P)：喜欢灵活开放的生活方式，适应性强，享受探索过程。'
        }
    }
    
    story.append(Paragraph('◆ 维度详解', section_style))
    for k, v in result.score_detail.items():
        if k in dim_explanations:
            exp = dim_explanations[k]
            story.append(Paragraph(f'<b>{exp["name"]}</b>', subsection_style))
            # 根据分数显示对应的解释
            if k == 'IE':
                letter = 'E' if v > 0 else 'I'
            elif k == 'SN':
                letter = 'S' if v > 0 else 'N'
            elif k == 'TF':
                letter = 'T' if v > 0 else 'F'
            else:
                letter = 'J' if v > 0 else 'P'
            story.append(Paragraph(exp[letter], list_style))
    
    story.append(Spacer(1, 0.5*cm))
    
    # ==================== 科研协作优势与发展建议 ====================
    if strengths:
        story.append(Paragraph('◆ 科研协作优势', section_style))
        story.append(Paragraph(strengths, body_style))
        story.append(Spacer(1, 0.5*cm))
    
    if growth:
        story.append(Paragraph('◆ 发展建议', section_style))
        story.append(Paragraph(growth, body_style))
        story.append(Spacer(1, 0.5*cm))

    # ==================== 多维度深度分析 ====================
    analysis_items = [
        ('科研偏好特点', getattr(profile, 'personality_traits', '') if profile else ''),
        ('研究工作风格', getattr(profile, 'work_style', '') if profile else ''),
        ('团队协作方式', getattr(profile, 'interpersonal_relations', '') if profile else ''),
        ('情感表达', getattr(profile, 'emotional_expression', '') if profile else ''),
        ('决策方式', getattr(profile, 'decision_making', '') if profile else ''),
        ('压力管理', getattr(profile, 'stress_management', '') if profile else ''),
        ('学习方式', getattr(profile, 'learning_style', '') if profile else ''),
        ('科研角色建议', getattr(profile, 'career_suggestions', '') if profile else ''),
        ('研究价值观', getattr(profile, 'life_philosophy', '') if profile else ''),
        ('沟通风格', getattr(profile, 'communication_style', '') if profile else ''),
    ]
    
    has_analysis = any(content for _, content in analysis_items)
    if has_analysis:
        story.append(PageBreak())
        story.append(Paragraph('◆ 多维度深度分析', section_style))
        story.append(Spacer(1, 0.3*cm))
    
        for title, content in analysis_items:
            if content:
                story.append(Paragraph(f'<b>• {title}</b>', subsection_style))
                story.append(Paragraph(content, list_style))
                story.append(Spacer(1, 0.2*cm))
    
    # ==================== 总结与寄语 ====================
    story.append(Spacer(1, 0.5*cm))
    story.append(Paragraph('◆ 总结与寄语', section_style))
    
    summary_text = f'''您的 MBTI-Research 科研协作画像是 {result.type_code} ({profile_name or "待完善"})。
    
每种科研协作画像都有其独特优势和潜在成长空间。MBTI-Research 结果仅供科研协作、自我理解和团队沟通参考，帮助您更好地了解自己的研究偏好、沟通方式和适合承担的协作角色。

请记住：
• 科研画像不是固定标签，更不代表科研能力高低
• 了解自己的倾向有助于更清楚地沟通、分工和寻求支持
• 接纳自己的工作方式，同时保持开放心态去训练新的能力
• 不同画像各有所长，互补协作能提高团队的研究质量

希望这份报告能帮助您在AI科研合作中更好地理解自己，也帮助导师和团队成员用更合适的方式协作。'''
    
    story.append(Paragraph(summary_text.replace('\n', '<br/>'), body_style))
    
    # ==================== 页脚 ====================
    story.append(Spacer(1, 2*cm))
    story.append(Paragraph('—' * 40, footer_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph('本报告由 MBTI-Research 生成，仅供科研协作参考', footer_style))
    story.append(Paragraph(f'报告生成时间：{now_local.strftime("%Y年%m月%d日 %H:%M")}', footer_style))
    story.append(Paragraph('京ICP备2025157088号', footer_style))

    # 构建PDF
    doc.build(story)
    buffer.seek(0)

    from django.http import HttpResponse
    response = HttpResponse(buffer, content_type='application/pdf')
    filename = f'MBTI-Research报告_{request.user.username}_{test_time.strftime("%Y%m%d")}.pdf'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
