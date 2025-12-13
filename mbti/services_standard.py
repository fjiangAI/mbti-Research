"""
标准MBTI 93题计分服务
按照官方MBTI计分规则实现
"""
from typing import Dict, Tuple
from django.db.models import QuerySet
from .models import Response, Question


class StandardMBTIScoringService:
    """标准MBTI 93题计分服务类"""
    
    # 标准MBTI 93题计分规则（严格按照官方MBTI规则）
    # 参考：MBTI人格量表记分规则
    
    # E-I维度计分规则（共21题）
    # 规则说明：
    # - E_A: 选A得E分的题目编号
    # - E_B: 选B得E分的题目编号（这些题目选B表示外向倾向）
    E_SCORING_RULES = {
        'E_A': [3, 7, 10, 19, 23, 32, 62, 74, 79, 81, 83],  # 11题：选A得E分
        'E_B': [13, 16, 26, 38, 42, 57, 68, 77, 85, 91],   # 10题：选B得E分
    }
    
    # S-N维度计分规则（共26题）
    # 规则说明：
    # - S_A: 选A得S分的题目编号
    # - S_B: 选B得S分的题目编号（这些题目选B表示感觉倾向）
    S_SCORING_RULES = {
        'S_A': [2, 9, 25, 30, 34, 39, 50, 52, 54, 60, 63, 73, 92],  # 13题：选A得S分
        'S_B': [5, 11, 18, 22, 27, 44, 46, 48, 65, 67, 69, 71, 82],  # 13题：选B得S分
    }
    
    # T-F维度计分规则（共24题）
    # 规则说明：
    # - T_A: 选A得T分的题目编号
    # - T_B: 选B得T分的题目编号（这些题目选B表示思考倾向）
    T_SCORING_RULES = {
        'T_A': [31, 33, 35, 43, 45, 47, 49, 56, 58, 61, 66, 75, 87],  # 13题：选A得T分
        'T_B': [6, 15, 21, 29, 37, 40, 51, 53, 70, 72, 89],  # 11题：选B得T分
    }
    
    # J-P维度计分规则（共22题）
    # 规则说明：
    # - J_A: 选A得J分的题目编号
    # - J_B: 选B得J分的题目编号（这些题目选B表示判断倾向）
    J_SCORING_RULES = {
        'J_A': [1, 4, 12, 14, 20, 28, 36, 41, 64, 76, 86],  # 11题：选A得J分
        'J_B': [8, 17, 24, 55, 59, 78, 80, 84, 88, 90, 93],  # 11题：选B得J分
    }
    
    # 维度总分
    DIMENSION_TOTALS = {
        'IE': 21,
        'SN': 26,
        'TF': 24,
        'JP': 22,
    }
    
    @staticmethod
    def _get_question_number(question: Question) -> int:
        """从题目中提取题目编号"""
        # 假设题目模型中有question_number字段，或者从order字段获取
        # 如果order就是题目编号，直接返回
        return getattr(question, 'question_number', None) or question.order
    
    @staticmethod
    def _map_choice_to_ab(choice: int) -> str:
        """
        将选择映射到A/B
        标准MBTI：1 = A, 2 = B
        """
        if choice == 1:
            return 'A'
        elif choice == 2:
            return 'B'
        else:
            return None  # 无效选择
    
    @staticmethod
    def calculate_scores_standard(responses: QuerySet[Response]) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        按照标准MBTI规则计算维度分数
        
        重要说明：
        - 标准MBTI 93题计分规则：
          * E-I维度：共21题，E_A题目选A得E分，I_B题目选B得E分
          * S-N维度：共26题，S_A题目选A得S分，N_B题目选B得S分
          * T-F维度：共24题，T_A题目选A得T分，F_B题目选B得T分
          * J-P维度：共22题，J_A题目选A得J分，P_B题目选B得J分
        - 对侧分数 = 维度总分 - 正向分数（如I = 21 - E）
        - 最终类型判断：每个维度选择分数较高的一方，相等时按规则选择（SN/TF/JP相等时选N/F/P）
        
        Args:
            responses: 用户的回答QuerySet（必须来自同一问卷）
            
        Returns:
            Tuple[维度原始分数字典, 题目数量字典]
        """
        # 初始化得分
        E_score = 0
        S_score = 0
        T_score = 0
        J_score = 0
        
        counts = {"IE": 0, "SN": 0, "TF": 0, "JP": 0}
        
        # 创建题目编号到回答的映射
        question_responses = {}
        for resp in responses.select_related('question'):
            q_num = StandardMBTIScoringService._get_question_number(resp.question)
            if q_num and q_num > 0:  # 确保题目编号有效
                # 标准MBTI：1 = A, 2 = B
                ab_choice = StandardMBTIScoringService._map_choice_to_ab(resp.choice)
                if ab_choice:
                    # 如果同一题目有多个回答，使用最新的（理论上不应该发生）
                    question_responses[q_num] = ab_choice
        
        # 计算E得分
        for q_num in StandardMBTIScoringService.E_SCORING_RULES['E_A']:
            if q_num in question_responses:
                ab_choice = question_responses[q_num]
                if ab_choice == 'A':
                    E_score += 1
                    counts['IE'] += 1
        
        for q_num in StandardMBTIScoringService.E_SCORING_RULES['E_B']:
            if q_num in question_responses:
                ab_choice = question_responses[q_num]
                if ab_choice == 'B':
                    E_score += 1
                    counts['IE'] += 1
        
        # 计算S得分
        for q_num in StandardMBTIScoringService.S_SCORING_RULES['S_A']:
            if q_num in question_responses:
                ab_choice = question_responses[q_num]
                if ab_choice == 'A':
                    S_score += 1
                    counts['SN'] += 1
        
        for q_num in StandardMBTIScoringService.S_SCORING_RULES['S_B']:
            if q_num in question_responses:
                ab_choice = question_responses[q_num]
                if ab_choice == 'B':
                    S_score += 1
                    counts['SN'] += 1
        
        # 计算T得分
        for q_num in StandardMBTIScoringService.T_SCORING_RULES['T_A']:
            if q_num in question_responses:
                ab_choice = question_responses[q_num]
                if ab_choice == 'A':
                    T_score += 1
                    counts['TF'] += 1
        
        for q_num in StandardMBTIScoringService.T_SCORING_RULES['T_B']:
            if q_num in question_responses:
                ab_choice = question_responses[q_num]
                if ab_choice == 'B':
                    T_score += 1
                    counts['TF'] += 1
        
        # 计算J得分
        for q_num in StandardMBTIScoringService.J_SCORING_RULES['J_A']:
            if q_num in question_responses:
                ab_choice = question_responses[q_num]
                if ab_choice == 'A':
                    J_score += 1
                    counts['JP'] += 1
        
        for q_num in StandardMBTIScoringService.J_SCORING_RULES['J_B']:
            if q_num in question_responses:
                ab_choice = question_responses[q_num]
                if ab_choice == 'B':
                    J_score += 1
                    counts['JP'] += 1
        
        # 计算对侧分数（按照标准MBTI规则）
        I_score = StandardMBTIScoringService.DIMENSION_TOTALS['IE'] - E_score
        N_score = StandardMBTIScoringService.DIMENSION_TOTALS['SN'] - S_score
        F_score = StandardMBTIScoringService.DIMENSION_TOTALS['TF'] - T_score
        P_score = StandardMBTIScoringService.DIMENSION_TOTALS['JP'] - J_score
        
        # 返回维度分数（原始分数，用于后续判断）
        # 格式：{"IE": {"E": 12, "I": 9}, ...}
        dims = {
            "IE": {"E": E_score, "I": I_score},
            "SN": {"S": S_score, "N": N_score},
            "TF": {"T": T_score, "F": F_score},
            "JP": {"J": J_score, "P": P_score},
        }
        
        return dims, counts
    
    @staticmethod
    def generate_type_code_standard(dims: Dict[str, Dict[str, int]]) -> str:
        """
        根据标准MBTI规则生成类型码
        
        Args:
            dims: 维度分数字典，格式：{"IE": {"E": 12, "I": 9}, ...}
            
        Returns:
            MBTI类型码（如 "INTJ"）
        """
        code = ""
        
        # IE维度：E > I 则选E，否则选I（相等时选I）
        ie_scores = dims["IE"]
        if ie_scores["E"] > ie_scores["I"]:
            code += "E"
        else:
            code += "I"  # E <= I 时选I（包括相等情况）
        
        # SN维度：S > N 则选S，否则选N（相等时选N）
        sn_scores = dims["SN"]
        if sn_scores["S"] > sn_scores["N"]:
            code += "S"
        else:
            code += "N"  # S <= N 时选N（包括相等情况）
        
        # TF维度：T > F 则选T，否则选F（相等时选F）
        tf_scores = dims["TF"]
        if tf_scores["T"] > tf_scores["F"]:
            code += "T"
        else:
            code += "F"  # T <= F 时选F（包括相等情况）
        
        # JP维度：J > P 则选J，否则选P（相等时选P）
        jp_scores = dims["JP"]
        if jp_scores["J"] > jp_scores["P"]:
            code += "J"
        else:
            code += "P"  # J <= P 时选P（包括相等情况）
        
        return code
    
    @staticmethod
    def get_preference_strength(score: int, dimension: str, pole: str) -> Tuple[str, str]:
        """
        获取偏好强度（按照标准MBTI规则）
        
        Args:
            score: 原始分数
            dimension: 维度代码（IE, SN, TF, JP）
            pole: 极性（E, I, S, N, T, F, J, P）
            
        Returns:
            Tuple[强度等级, 描述]
        """
        # 标准MBTI偏好强度分类
        if dimension == "IE":
            # E(I)=11-13: 轻微偏好
            # E(I)=14-16: 中等程度
            # E(I)=17-19: 明确偏好
            # E(I)=20-21: 绝对偏好
            if 11 <= score <= 13:
                level = "轻微"
            elif 14 <= score <= 16:
                level = "中等"
            elif 17 <= score <= 19:
                level = "明确"
            elif 20 <= score <= 21:
                level = "绝对"
            else:
                level = "轻微"
        elif dimension == "SN":
            # S(N)=13-15: 轻微偏好
            # S(N)=16-20: 中等程度
            # S(N)=21-24: 明确偏好
            # S(N)=25-26: 绝对偏好
            if 13 <= score <= 15:
                level = "轻微"
            elif 16 <= score <= 20:
                level = "中等"
            elif 21 <= score <= 24:
                level = "明确"
            elif 25 <= score <= 26:
                level = "绝对"
            else:
                level = "轻微"
        elif dimension == "TF":
            # T(F)=12-14: 轻微偏好
            # T(F)=16-20: 中等程度
            # T(F)=21-24: 明确偏好
            # T(F)=25-26: 绝对偏好（但TF总分是24，所以应该是21-24）
            if 12 <= score <= 14:
                level = "轻微"
            elif 16 <= score <= 20:
                level = "中等"
            elif 21 <= score <= 24:
                level = "明确"
            else:
                level = "轻微"
        elif dimension == "JP":
            # J(P)=11-13: 轻微偏好
            # J(P)=14-16: 中等程度
            # J(P)=17-20: 明确偏好
            # J(P)=21-22: 绝对偏好
            if 11 <= score <= 13:
                level = "轻微"
            elif 14 <= score <= 16:
                level = "中等"
            elif 17 <= score <= 20:
                level = "明确"
            elif 21 <= score <= 22:
                level = "绝对"
            else:
                level = "轻微"
        else:
            level = "轻微"
        
        return level, f"{level}偏好"

