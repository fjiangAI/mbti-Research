#!/usr/bin/env python
"""
验证标准MBTI 93题计分规则的正确性
"""
import os
import sys
import csv

# 添加项目根目录到Python路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

# 读取CSV文件，验证计分规则
csv_path = os.path.join(BASE_DIR, 'data', 'questions_standard_mbti_93.csv')

# 标准MBTI计分规则（从services_standard.py中提取）
E_SCORING_RULES = {
    'E_A': [3, 7, 10, 19, 23, 32, 62, 74, 79, 81, 83],
    'I_B': [13, 16, 26, 38, 42, 57, 68, 77, 85, 91],
}

S_SCORING_RULES = {
    'S_A': [2, 9, 25, 30, 34, 39, 50, 52, 54, 60, 63, 73, 92],
    'N_B': [5, 11, 18, 22, 27, 44, 46, 48, 65, 67, 69, 71, 82],
}

T_SCORING_RULES = {
    'T_A': [31, 33, 35, 43, 45, 47, 49, 56, 58, 61, 66, 75, 87],
    'F_B': [6, 15, 21, 29, 37, 40, 51, 53, 70, 72, 89],
}

J_SCORING_RULES = {
    'J_A': [1, 4, 12, 14, 20, 28, 36, 41, 64, 76, 86],
    'P_B': [8, 17, 24, 55, 59, 78, 80, 84, 88, 90, 93],
}

def validate_scoring_rules():
    """验证计分规则与CSV文件的一致性"""
    print("=" * 80)
    print("验证标准MBTI 93题计分规则")
    print("=" * 80)
    
    # 读取CSV文件
    questions_by_number = {}
    questions_by_rule = {}
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                q_num = int(row.get('question_number', 0))
                dimension = row.get('dimension', '').strip()
                scoring_rule = row.get('scoring_rule', '').strip()
                
                if q_num > 0:
                    questions_by_number[q_num] = {
                        'dimension': dimension,
                        'scoring_rule': scoring_rule,
                        'text': row.get('text', '')[:50]  # 只取前50个字符
                    }
                    
                    if scoring_rule:
                        if scoring_rule not in questions_by_rule:
                            questions_by_rule[scoring_rule] = []
                        questions_by_rule[scoring_rule].append(q_num)
            except (ValueError, KeyError) as e:
                continue
    
    print(f"\n总共读取 {len(questions_by_number)} 道题目")
    
    # 验证E-I维度
    print("\n" + "=" * 80)
    print("验证 E-I 维度计分规则")
    print("=" * 80)
    
    e_a_found = set()
    i_b_found = set()
    
    for q_num in E_SCORING_RULES['E_A']:
        if q_num in questions_by_number:
            q = questions_by_number[q_num]
            if q['scoring_rule'] == 'E_A' and q['dimension'] == 'IE':
                e_a_found.add(q_num)
                print(f"✓ 题目 {q_num}: {q['text']} - {q['scoring_rule']}")
            else:
                print(f"✗ 题目 {q_num}: 规则不匹配！期望 E_A/IE，实际 {q['scoring_rule']}/{q['dimension']}")
        else:
            print(f"✗ 题目 {q_num}: 未找到")
    
    for q_num in E_SCORING_RULES['I_B']:
        if q_num in questions_by_number:
            q = questions_by_number[q_num]
            if q['scoring_rule'] == 'I_B' and q['dimension'] == 'IE':
                i_b_found.add(q_num)
                print(f"✓ 题目 {q_num}: {q['text']} - {q['scoring_rule']}")
            else:
                print(f"✗ 题目 {q_num}: 规则不匹配！期望 I_B/IE，实际 {q['scoring_rule']}/{q['dimension']}")
        else:
            print(f"✗ 题目 {q_num}: 未找到")
    
    print(f"\nE_A规则: 期望 {len(E_SCORING_RULES['E_A'])} 题，找到 {len(e_a_found)} 题")
    print(f"I_B规则: 期望 {len(E_SCORING_RULES['I_B'])} 题，找到 {len(i_b_found)} 题")
    print(f"E-I维度总计: {len(e_a_found) + len(i_b_found)} 题（期望21题）")
    
    # 验证S-N维度
    print("\n" + "=" * 80)
    print("验证 S-N 维度计分规则")
    print("=" * 80)
    
    s_a_found = set()
    n_b_found = set()
    
    for q_num in S_SCORING_RULES['S_A']:
        if q_num in questions_by_number:
            q = questions_by_number[q_num]
            if q['scoring_rule'] == 'S_A' and q['dimension'] == 'SN':
                s_a_found.add(q_num)
            else:
                print(f"✗ 题目 {q_num}: 规则不匹配！期望 S_A/SN，实际 {q['scoring_rule']}/{q['dimension']}")
        else:
            print(f"✗ 题目 {q_num}: 未找到")
    
    for q_num in S_SCORING_RULES['N_B']:
        if q_num in questions_by_number:
            q = questions_by_number[q_num]
            if q['scoring_rule'] == 'N_B' and q['dimension'] == 'SN':
                n_b_found.add(q_num)
            else:
                print(f"✗ 题目 {q_num}: 规则不匹配！期望 N_B/SN，实际 {q['scoring_rule']}/{q['dimension']}")
        else:
            print(f"✗ 题目 {q_num}: 未找到")
    
    print(f"\nS_A规则: 期望 {len(S_SCORING_RULES['S_A'])} 题，找到 {len(s_a_found)} 题")
    print(f"N_B规则: 期望 {len(S_SCORING_RULES['N_B'])} 题，找到 {len(n_b_found)} 题")
    print(f"S-N维度总计: {len(s_a_found) + len(n_b_found)} 题（期望26题）")
    
    # 验证T-F维度
    print("\n" + "=" * 80)
    print("验证 T-F 维度计分规则")
    print("=" * 80)
    
    t_a_found = set()
    f_b_found = set()
    
    for q_num in T_SCORING_RULES['T_A']:
        if q_num in questions_by_number:
            q = questions_by_number[q_num]
            if q['scoring_rule'] == 'T_A' and q['dimension'] == 'TF':
                t_a_found.add(q_num)
            else:
                print(f"✗ 题目 {q_num}: 规则不匹配！期望 T_A/TF，实际 {q['scoring_rule']}/{q['dimension']}")
        else:
            print(f"✗ 题目 {q_num}: 未找到")
    
    for q_num in T_SCORING_RULES['F_B']:
        if q_num in questions_by_number:
            q = questions_by_number[q_num]
            if q['scoring_rule'] == 'F_B' and q['dimension'] == 'TF':
                f_b_found.add(q_num)
            else:
                print(f"✗ 题目 {q_num}: 规则不匹配！期望 F_B/TF，实际 {q['scoring_rule']}/{q['dimension']}")
        else:
            print(f"✗ 题目 {q_num}: 未找到")
    
    print(f"\nT_A规则: 期望 {len(T_SCORING_RULES['T_A'])} 题，找到 {len(t_a_found)} 题")
    print(f"F_B规则: 期望 {len(T_SCORING_RULES['F_B'])} 题，找到 {len(f_b_found)} 题")
    print(f"T-F维度总计: {len(t_a_found) + len(f_b_found)} 题（期望24题）")
    
    # 验证J-P维度
    print("\n" + "=" * 80)
    print("验证 J-P 维度计分规则")
    print("=" * 80)
    
    j_a_found = set()
    p_b_found = set()
    
    for q_num in J_SCORING_RULES['J_A']:
        if q_num in questions_by_number:
            q = questions_by_number[q_num]
            if q['scoring_rule'] == 'J_A' and q['dimension'] == 'JP':
                j_a_found.add(q_num)
            else:
                print(f"✗ 题目 {q_num}: 规则不匹配！期望 J_A/JP，实际 {q['scoring_rule']}/{q['dimension']}")
        else:
            print(f"✗ 题目 {q_num}: 未找到")
    
    for q_num in J_SCORING_RULES['P_B']:
        if q_num in questions_by_number:
            q = questions_by_number[q_num]
            if q['scoring_rule'] == 'P_B' and q['dimension'] == 'JP':
                p_b_found.add(q_num)
            else:
                print(f"✗ 题目 {q_num}: 规则不匹配！期望 P_B/JP，实际 {q['scoring_rule']}/{q['dimension']}")
        else:
            print(f"✗ 题目 {q_num}: 未找到")
    
    print(f"\nJ_A规则: 期望 {len(J_SCORING_RULES['J_A'])} 题，找到 {len(j_a_found)} 题")
    print(f"P_B规则: 期望 {len(J_SCORING_RULES['P_B'])} 题，找到 {len(p_b_found)} 题")
    print(f"J-P维度总计: {len(j_a_found) + len(p_b_found)} 题（期望22题）")
    
    # 总结
    print("\n" + "=" * 80)
    print("验证总结")
    print("=" * 80)
    total_expected = 21 + 26 + 24 + 22
    total_found = (len(e_a_found) + len(i_b_found) + 
                   len(s_a_found) + len(n_b_found) + 
                   len(t_a_found) + len(f_b_found) + 
                   len(j_a_found) + len(p_b_found))
    
    print(f"总题目数: {total_found}/{total_expected} (期望93题)")
    
    if total_found == total_expected:
        print("✓ 所有计分规则验证通过！")
    else:
        print("✗ 计分规则验证失败，请检查题目编号和规则匹配！")

if __name__ == '__main__':
    validate_scoring_rules()


