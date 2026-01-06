#!/usr/bin/env python
"""
从JSON文件导入标准MBTI 93题题库
"""
import os
import sys
import json

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbti_site.settings')

import django
django.setup()

from mbti.models import Questionnaire, Question
from mbti.services_standard import StandardMBTIScoringService

def load_questions_from_json(json_path):
    """从JSON文件加载题目"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_question_dimension_and_pole(question_id):
    """根据题目编号从计分规则中推断dimension和keyed_pole"""
    # 检查E-I维度
    # E_A: 选A得E分的题目
    # I_B: 选B得E分的题目（反向计分）
    if question_id in StandardMBTIScoringService.E_SCORING_RULES['E_A']:
        return 'IE', 'E'
    elif question_id in StandardMBTIScoringService.E_SCORING_RULES['I_B']:
        return 'IE', 'I'
    
    # 检查S-N维度
    # S_A: 选A得S分的题目
    # N_B: 选B得S分的题目（反向计分）
    if question_id in StandardMBTIScoringService.S_SCORING_RULES['S_A']:
        return 'SN', 'S'
    elif question_id in StandardMBTIScoringService.S_SCORING_RULES['N_B']:
        return 'SN', 'N'
    
    # 检查T-F维度
    # T_A: 选A得T分的题目
    # F_B: 选B得T分的题目（反向计分）
    if question_id in StandardMBTIScoringService.T_SCORING_RULES['T_A']:
        return 'TF', 'T'
    elif question_id in StandardMBTIScoringService.T_SCORING_RULES['F_B']:
        return 'TF', 'F'
    
    # 检查J-P维度
    # J_A: 选A得J分的题目
    # P_B: 选B得J分的题目（反向计分）
    if question_id in StandardMBTIScoringService.J_SCORING_RULES['J_A']:
        return 'JP', 'J'
    elif question_id in StandardMBTIScoringService.J_SCORING_RULES['P_B']:
        return 'JP', 'P'
    
    # 默认值（不应该发生）
    return 'IE', 'I'

def import_questions_from_json(json_path):
    """从JSON文件导入题目到数据库"""
    print("=" * 80)
    print("从JSON文件导入标准MBTI 93题题库")
    print("=" * 80)
    
    # 获取或创建问卷
    qnn, created = Questionnaire.objects.get_or_create(
        key='mbti_standard_93',
        defaults={
            'name': '标准MBTI 93题测试',
            'description': '标准MBTI人格类型测试，共93题',
            'is_active': True
        }
    )
    
    if created:
        print(f"✓ 创建新问卷: {qnn.name}")
    else:
        print(f"✓ 使用现有问卷: {qnn.name}")
        # 清除该问卷下的旧题目
        old_count = Question.objects.filter(questionnaire=qnn).count()
        if old_count > 0:
            Question.objects.filter(questionnaire=qnn).delete()
            print(f"✓ 已清除 {old_count} 道旧题目")
    
    # 加载JSON数据
    try:
        questions_data = load_questions_from_json(json_path)
        print(f"✓ 成功加载 {len(questions_data)} 道题目")
    except Exception as e:
        print(f"✗ 加载JSON文件失败: {e}")
        return
    
    # 导入题目
    created_count = 0
    updated_count = 0
    
    for item in questions_data:
        question_id = item.get('id')
        question_text = item.get('question', '').strip()
        option_a = item.get('optionA', '').strip()
        option_b = item.get('optionB', '').strip()
        
        if not question_text or not option_a or not option_b:
            print(f"⚠️  题目 {question_id} 数据不完整，跳过")
            continue
        
        # 构造完整的题目文本（包含选项）
        full_text = f"{question_id}. {question_text} A) {option_a} B) {option_b}"
        
        # 从计分规则中推断dimension和keyed_pole
        dimension, keyed_pole = get_question_dimension_and_pole(question_id)
        
        # 创建或更新题目（使用order作为唯一标识，因为模型没有question_number字段）
        question, created = Question.objects.update_or_create(
            questionnaire=qnn,
            order=question_id,
            defaults={
                'text': full_text,
                'dimension': dimension,
                'keyed_pole': keyed_pole,
                'weight': 1,
                'active': True,
            }
        )
        
        if created:
            created_count += 1
        else:
            updated_count += 1
    
    print("=" * 80)
    print(f"导入完成！")
    print(f"  - 新建: {created_count} 道")
    print(f"  - 更新: {updated_count} 道")
    print(f"  - 总计: {created_count + updated_count} 道")
    print("=" * 80)

if __name__ == '__main__':
    json_path = os.path.join(BASE_DIR, 'data', 'questions_standard_mbti_93.json')
    if not os.path.exists(json_path):
        print(f"✗ JSON文件不存在: {json_path}")
        sys.exit(1)
    
    import_questions_from_json(json_path)

