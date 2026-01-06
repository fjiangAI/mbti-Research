"""
标准MBTI 93题计分服务
按照官方MBTI计分规则实现
"""
from typing import Dict, Tuple
from django.db.models import QuerySet
from .models import Response, Question


class StandardMBTIScoringService:
    """标准MBTI 93题计分服务类"""
    
    # 标准MBTI计分规则
    # E-I维度计分规则
    E_SCORING_RULES = {
        'E_A': [3, 7, 10, 19, 23, 32, 62, 74, 79, 81, 83],  # 选A得E分
        'I_B': [13, 16, 26, 38, 42, 57, 68, 77, 85, 91],   # 选B得E分（实际是I的反向）
    }
    
    # S-N维度计分规则
    S_SCORING_RULES = {
        'S_A': [2, 9, 25, 30, 34, 39, 50, 52, 54, 60, 63, 73, 92],  # 选A得S分
        'N_B': [5, 11, 18, 22, 27, 44, 46, 48, 65, 67, 69, 71, 82],  # 选B得S分（实际是N的反向）
    }
    
    # T-F维度计分规则
    T_SCORING_RULES = {
        'T_A': [31, 33, 35, 43, 45, 47, 49, 56, 58, 61, 66, 75, 87],  # 选A得T分
        'F_B': [6, 15, 21, 29, 37, 40, 51, 53, 70, 72, 89],  # 选B得T分（实际是F的反向）
    }
    
    # J-P维度计分规则
    J_SCORING_RULES = {
        'J_A': [1, 4, 12, 14, 20, 28, 36, 41, 64, 76, 86],  # 选A得J分
        'P_B': [8, 17, 24, 55, 59, 78, 80, 84, 88, 90, 93],  # 选B得J分（实际是P的反向）
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
        
        Args:
            responses: 用户的回答QuerySet
            
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
            if q_num:
                # 标准MBTI：1 = A, 2 = B
                ab_choice = StandardMBTIScoringService._map_choice_to_ab(resp.choice)
                if ab_choice:
                    question_responses[q_num] = ab_choice
        
        # 计算E得分
        for q_num in StandardMBTIScoringService.E_SCORING_RULES['E_A']:
            if q_num in question_responses:
                ab_choice = question_responses[q_num]
                if ab_choice == 'A':
                    E_score += 1
                    counts['IE'] += 1
        
        for q_num in StandardMBTIScoringService.E_SCORING_RULES['I_B']:
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
        
        for q_num in StandardMBTIScoringService.S_SCORING_RULES['N_B']:
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
        
        for q_num in StandardMBTIScoringService.T_SCORING_RULES['F_B']:
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
        
        for q_num in StandardMBTIScoringService.J_SCORING_RULES['P_B']:
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
        
        # IE维度：E > I 则选E，否则选I
        ie_scores = dims["IE"]
        if ie_scores["E"] > ie_scores["I"]:
            code += "E"
        else:
            code += "I"
        
        # SN维度：S > N 则选S，否则选N（相等时选N）
        sn_scores = dims["SN"]
        if sn_scores["S"] > sn_scores["N"]:
            code += "S"
        else:
            code += "N"
        
        # TF维度：T > F 则选T，否则选F（相等时选F）
        tf_scores = dims["TF"]
        if tf_scores["T"] > tf_scores["F"]:
            code += "T"
        else:
            code += "F"
        
        # JP维度：J > P 则选J，否则选P（相等时选P）
        jp_scores = dims["JP"]
        if jp_scores["J"] > jp_scores["P"]:
            code += "J"
        else:
            code += "P"
        
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

