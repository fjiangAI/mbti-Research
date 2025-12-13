"""
MBTI测试计分服务
负责处理测试结果的计分逻辑
"""
from typing import Dict, Tuple
from django.db.models import QuerySet
from .models import Response, Question


class MBTIScoringService:
    """MBTI测试计分服务类"""
    
    # 维度映射
    DIMENSION_MAP = {
        "IE": ("I", "E"),
        "SN": ("S", "N"),
        "TF": ("T", "F"),
        "JP": ("J", "P"),
    }
    
    # 每页题目数量
    QUESTIONS_PER_PAGE = 10
    
    @staticmethod
    def calculate_scores(responses: QuerySet[Response]) -> Tuple[Dict[str, float], Dict[str, int]]:
        """
        计算MBTI维度分数
        
        Args:
            responses: 用户的回答QuerySet
            
        Returns:
            Tuple[维度分数字典, 题目数量字典]
        """
        dims = {"IE": 0.0, "SN": 0.0, "TF": 0.0, "JP": 0.0}
        counts = {"IE": 0, "SN": 0, "TF": 0, "JP": 0}
        
        for resp in responses.select_related('question'):
            dim = resp.question.dimension
            if dim not in dims:
                continue
                
            # 验证答案范围
            if not (1 <= resp.choice <= 5):
                continue
            
            # 标准化计分：Likert(1..5)→[-2..+2]
            raw = resp.choice - 3  # -2..+2
            
            pole_pair = MBTIScoringService.DIMENSION_MAP[dim]
            
            # 若题目倾向的是第二极性（如E、N、F、P），则正向；否则反向
            direction = 1 if resp.question.keyed_pole == pole_pair[1] else -1
            
            # 应用权重
            weight = max(1, resp.question.weight)
            score = raw * direction * weight
            
            dims[dim] += score
            counts[dim] += 1
        
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
        for dim, score in dims.items():
            pole_pair = MBTIScoringService.DIMENSION_MAP[dim]
            # v > 0 代表维度字符串的第二极性（如 IE 中的 E）
            # v <= 0 代表第一极性（如 I）
            # 注意：当分数为0时，默认选择第一极性
            code += pole_pair[1] if score > 0 else pole_pair[0]
        return code
    
    @staticmethod
    def calculate_confidence(dims: Dict[str, float], counts: Dict[str, int]) -> Dict[str, float]:
        """
        计算各维度的置信度
        
        Args:
            dims: 维度分数字典
            counts: 题目数量字典
            
        Returns:
            置信度字典（0..1）
        """
        confidence = {}
        for dim, score in dims.items():
            n = max(counts[dim], 1)
            
            # 改进的置信度计算：
            # 考虑每题最大可能分值（假设weight=1时，每题最大绝对分值为2）
            # 平均绝对分值 / 2 归一化到 [0, 1]
            avg_abs_score = abs(score) / n
            confidence[dim] = min(1.0, max(0.0, avg_abs_score / 2.0))
        
        return confidence
    
    @staticmethod
    def validate_responses(responses: QuerySet[Response], required_question_ids: set) -> Tuple[bool, int]:
        """
        验证回答是否完整
        
        Args:
            responses: 用户的回答QuerySet
            required_question_ids: 必需的题目ID集合
            
        Returns:
            Tuple[是否完整, 缺失题目数量]
        """
        answered_ids = set(responses.values_list('question_id', flat=True))
        missing_ids = required_question_ids - answered_ids
        return len(missing_ids) == 0, len(missing_ids)
    
    @staticmethod
    def get_dimension_tendency(dim: str, score: float) -> Tuple[str, str]:
        """
        获取维度倾向
        
        Args:
            dim: 维度代码（如 "IE"）
            score: 维度分数
            
        Returns:
            Tuple[倾向字母, 倾向描述]
        """
        pole_pair = MBTIScoringService.DIMENSION_MAP[dim]
        tendency_map = {
            "IE": ("内向", "外向"),
            "SN": ("感觉", "直觉"),
            "TF": ("思考", "情感"),
            "JP": ("判断", "知觉"),
        }
        
        if score > 0:
            return pole_pair[1], tendency_map[dim][1]
        else:
            return pole_pair[0], tendency_map[dim][0]


