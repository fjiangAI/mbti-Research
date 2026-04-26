#!/usr/bin/env python
"""
初始化数据库脚本
1. 导入标准MBTI 93题题库
2. 创建Django后台管理员账号
"""
import os
import sys
import csv

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbti_site.settings')
django.setup()

from django.contrib.auth import get_user_model
from mbti.models import Question, Questionnaire, TypeProfile

User = get_user_model()


def load_standard_questions(csv_path):
    """加载标准MBTI 93题，合并成对的单词选择"""
    items = []
    paired_questions = {}  # 用于存储成对的题目 {question_number: {dimension, options, order}}
    processed_questions = set()  # 记录已处理的题目编号，避免重复
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row_num, row in enumerate(reader, start=2):  # 从第2行开始（第1行是标题）
            try:
                text = (row.get('text') or '').strip().strip('"')  # 去除引号
                dimension = (row.get('dimension') or '').strip().upper()
                keyed_pole = (row.get('keyed_pole') or '').strip().upper()
                
                # 安全地解析 question_number
                qn_str = (row.get('question_number') or '').strip()
                try:
                    question_number = int(qn_str) if qn_str else 0
                except ValueError:
                    print(f"[WARN] 第 {row_num} 行 question_number 格式错误: {qn_str}，跳过")
                    continue
                
                scoring_rule = (row.get('scoring_rule') or '').strip()
                
                # 安全地解析 weight
                weight_str = (row.get('weight') or '1').strip()
                try:
                    weight = int(weight_str) if weight_str else 1
                except ValueError:
                    weight = 1
                
                # 安全地解析 order
                order_str = (row.get('order') or str(question_number)).strip()
                try:
                    order = int(order_str) if order_str else question_number
                except ValueError:
                    order = question_number
                
                if not text or dimension not in ['IE', 'SN', 'TF', 'JP']:
                    print(f"[WARN] 第 {row_num} 行数据不完整，跳过")
                    continue
                
                # 判断是否是成对的单词选择（第二部分：27-73题，且文本中没有A)或B)）
                is_paired_choice = (27 <= question_number <= 73) and "A)" not in text and "B)" not in text
                
                if is_paired_choice:
                    # 成对的单词选择，需要合并
                    if question_number not in paired_questions:
                        paired_questions[question_number] = {
                            'dimension': dimension,
                            'options': [],
                            'order': order,
                        }
                    
                    # 确定这是A选项还是B选项
                    is_option_a = scoring_rule.endswith('_A')
                    
                    paired_questions[question_number]['options'].append({
                        'text': text,
                        'keyed_pole': keyed_pole,
                        'is_a': is_option_a,
                        'scoring_rule': scoring_rule,
                    })
                else:
                    # 第一部分和第三部分，直接添加（但要去除已处理的成对题目）
                    if question_number not in processed_questions:
                        items.append({
                            'text': text,
                            'dimension': dimension,
                            'keyed_pole': keyed_pole,
                            'question_number': question_number,
                            'scoring_rule': scoring_rule,
                            'weight': weight,
                            'order': order,
                        })
                        processed_questions.add(question_number)
            except Exception as e:
                print(f"[ERROR] 第 {row_num} 行处理失败: {e}，跳过")
                continue
    
    # 处理成对的题目，合并成一个题目
    for q_num, pair_data in sorted(paired_questions.items()):
        options = pair_data['options']
        if len(options) == 2:
            # 按A/B顺序排序（A在前）
            options.sort(key=lambda x: not x['is_a'])
            
            # 构建合并后的题目文本
            combined_text = f"你更容易喜欢或倾向哪一个词? A) {options[0]['text']} B) {options[1]['text']}"
            
            items.append({
                'text': combined_text,
                'dimension': pair_data['dimension'],
                'keyed_pole': options[0]['keyed_pole'],  # 使用第一个选项的keyed_pole
                'question_number': q_num,
                'scoring_rule': options[0]['scoring_rule'],
                'weight': 1,
                'order': pair_data['order'],
            })
            processed_questions.add(q_num)
        else:
            print(f"[WARN] 题目 {q_num} 的选项数量不是2（实际{len(options)}），跳过合并")
    
    # 按order排序
    items.sort(key=lambda x: x['order'])
    print(f"[INFO] 合并后共 {len(items)} 题（标准MBTI应为93题）")
    return items


def import_questions():
    """导入标准MBTI题库（从JSON文件）"""
    print("=" * 50)
    print("开始导入标准MBTI题库...")
    print("=" * 50)
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 项目根目录
    json_path = os.path.join(BASE_DIR, 'data', 'questions_standard_mbti_93.json')
    
    if not os.path.exists(json_path):
        print(f"❌ 题库文件不存在：{json_path}")
        return False
    
    # 使用JSON导入脚本
    try:
        from database_management.add_questions_from_json import import_questions_from_json
        import_questions_from_json(json_path)
        return True
    except Exception as e:
        print(f"❌ 导入失败：{e}")
        import traceback
        traceback.print_exc()
        return False


def create_admin_user():
    """创建Django后台管理员账号"""
    print("\n" + "=" * 50)
    print("创建Django后台管理员账号...")
    print("=" * 50)
    
    USERNAME = 'admin'
    EMAIL = 'admin@example.com'
    PASSWORD = 'admin@123..'
    
    # 检查用户是否已存在
    if User.objects.filter(username=USERNAME).exists():
        print(f"用户 {USERNAME} 已存在，更新密码...")
        user = User.objects.get(username=USERNAME)
        user.set_password(PASSWORD)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        print(f"✓ 已更新用户 {USERNAME} 的密码")
    else:
        # 创建新用户
        user = User.objects.create_superuser(
            username=USERNAME,
            email=EMAIL,
            password=PASSWORD
        )
        print(f"✓ 已创建管理员账号：{USERNAME}")
    
    print(f"\n管理员账号信息：")
    print(f"  用户名: {USERNAME}")
    print(f"  密码: {PASSWORD}")
    print(f"  访问地址: http://localhost:8989/admin/")


def main():
    """主函数"""
    print("\n" + "=" * 50)
    print("数据库初始化脚本")
    print("=" * 50)
    
    # 1. 导入题库
    if not import_questions():
        print("❌ 题库导入失败，终止初始化")
        sys.exit(1)
    
    # 2. 创建管理员账号
    create_admin_user()
    
    print("\n" + "=" * 50)
    print("✅ 数据库初始化完成！")
    print("=" * 50)
    print("\n下一步：")
    print("1. 访问 http://localhost:8989/admin/ 登录管理后台")
    print("2. 使用账号 admin / admin@123.. 登录")
    print("3. 可以导入16种科研协作画像数据：python populate_personality_data.py")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

