#!/usr/bin/env python
"""
清空数据库脚本
清空所有测试相关的数据：题目、回答、结果、用户等
"""
import os
import sys

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mbti_site.settings')
django.setup()

from django.contrib.auth import get_user_model
from mbti.models import Question, Response, Result, Questionnaire, TypeProfile

User = get_user_model()

def clear_database():
    """清空数据库"""
    print("=" * 50)
    print("开始清空数据库...")
    print("=" * 50)
    
    # 统计删除前的数量
    question_count = Question.objects.count()
    response_count = Response.objects.count()
    result_count = Result.objects.count()
    questionnaire_count = Questionnaire.objects.count()
    user_count = User.objects.count()
    typeprofile_count = TypeProfile.objects.count()
    
    print(f"\n删除前统计：")
    print(f"  题目: {question_count}")
    print(f"  回答: {response_count}")
    print(f"  结果: {result_count}")
    print(f"  问卷: {questionnaire_count}")
    print(f"  用户: {user_count}")
    print(f"  类型档案: {typeprofile_count}")
    
    # 确认
    confirm = input("\n⚠️  确定要清空所有数据吗？(yes/no): ")
    if confirm.lower() != 'yes':
        print("❌ 操作已取消")
        return
    
    print("\n开始删除...")
    
    # 删除回答（必须先删除，因为有外键依赖）
    deleted_responses = Response.objects.all().delete()[0]
    print(f"✓ 删除回答: {deleted_responses} 条")
    
    # 删除结果
    deleted_results = Result.objects.all().delete()[0]
    print(f"✓ 删除结果: {deleted_results} 条")
    
    # 删除题目
    deleted_questions = Question.objects.all().delete()[0]
    print(f"✓ 删除题目: {deleted_questions} 条")
    
    # 删除问卷
    deleted_questionnaires = Questionnaire.objects.all().delete()[0]
    print(f"✓ 删除问卷: {deleted_questionnaires} 条")
    
    # 删除类型档案
    deleted_profiles = TypeProfile.objects.all().delete()[0]
    print(f"✓ 删除类型档案: {deleted_profiles} 条")
    
    # 删除用户（除了超级用户）
    deleted_users = User.objects.filter(is_superuser=False).delete()[0]
    print(f"✓ 删除普通用户: {deleted_users} 条")
    
    print("\n" + "=" * 50)
    print("✅ 数据库清空完成！")
    print("=" * 50)
    
    # 显示剩余数据
    print(f"\n剩余数据：")
    print(f"  超级用户: {User.objects.filter(is_superuser=True).count()}")
    print(f"  题目: {Question.objects.count()}")
    print(f"  回答: {Response.objects.count()}")
    print(f"  结果: {Result.objects.count()}")


if __name__ == '__main__':
    try:
        clear_database()
    except KeyboardInterrupt:
        print("\n\n❌ 操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

