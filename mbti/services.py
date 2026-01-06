"""
MBTI计分服务（Likert量表版本）
用于非标准MBTI测试的计分逻辑
"""
from typing import Dict, Tuple
from django.db.models import QuerySet
from .models import Response


class MBTIScoringService:
    """MBTI Likert量表计分服务类"""
    
    # 每页显示的题目数
    QUESTIONS_PER_PAGE = 10
    
    # 维度映射
    DIMENSION_MAP = {
        'IE': ('I', 'E'),
        'SN': ('S', 'N'),
        'TF': ('T', 'F'),
        'JP': ('J', 'P'),
    }
    
    @staticmethod
    def calculate_scores(responses: QuerySet[Response]) -> Tuple[Dict[str, float], Dict[str, int]]:
        """
        计算各维度的分数（基于Likert量表）
        
        Args:
            responses: 用户的回答QuerySet
            
        Returns:
            Tuple[维度分数字典, 题目数量字典]
        """
        dims = {"IE": 0.0, "SN": 0.0, "TF": 0.0, "JP": 0.0}
        counts = {"IE": 0, "SN": 0, "TF": 0, "JP": 0}
        
        for resp in responses.select_related('question'):
            question = resp.question
            dimension = question.dimension
            keyed_pole = question.keyed_pole
            choice = resp.choice
            
            if dimension not in dims:
                continue
            
            # Likert量表：1-7分，4为中点
            # 转换为-3到+3的分数
            score = (choice - 4) * question.weight
            
            # 根据keyed_pole确定分数方向
            # 如果keyed_pole是维度的第一个字母（如IE中的I），正向计分
            # 否则反向计分
            dim_poles = MBTIScoringService.DIMENSION_MAP.get(dimension, ('', ''))
            if keyed_pole == dim_poles[0]:
                dims[dimension] -= score  # 偏向第一个极性
            else:
                dims[dimension] += score  # 偏向第二个极性
            
            counts[dimension] += 1
        
        return dims, counts
    
    @staticmethod
    def generate_type_code(dims: Dict[str, float]) -> str:
        """
        根据维度分数生成MBTI类型码
        
        Args:
            dims: 维度分数字典
            
        Returns:
            MBTI类型码（如 "INTJ"）
        """
        code = ""
        
        # IE维度
        code += "E" if dims.get("IE", 0) > 0 else "I"
        
        # SN维度
        code += "N" if dims.get("SN", 0) > 0 else "S"
        
        # TF维度
        code += "F" if dims.get("TF", 0) > 0 else "T"
        
        # JP维度
        code += "P" if dims.get("JP", 0) > 0 else "J"
        
        return code
    
    @staticmethod
    def calculate_confidence(dims: Dict[str, float], counts: Dict[str, int]) -> Dict[str, float]:
        """
        计算各维度的置信度
        
        Args:
            dims: 维度分数字典
            counts: 各维度题目数量
            
        Returns:
            各维度置信度字典（0-1之间）
        """
        confidence = {}
        
        for dim, score in dims.items():
            count = counts.get(dim, 0)
            if count > 0:
                # 最大可能分数 = 题目数 * 3（每题最大偏移3分）
                max_score = count * 3
                # 置信度 = 实际偏移 / 最大可能偏移
                confidence[dim] = min(abs(score) / max_score, 1.0) if max_score > 0 else 0.0
            else:
                confidence[dim] = 0.0
        
        return confidence

