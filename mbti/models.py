from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


class Questionnaire(models.Model):
    key = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name


class Question(models.Model):
    """MBTI测试题目模型"""
    
    # 维度定义
    DIMENSIONS = {
        'IE': ('I', 'E'),
        'SN': ('S', 'N'),
        'TF': ('T', 'F'),
        'JP': ('J', 'P'),
    }
    
    text = models.CharField(max_length=255)
    dimension = models.CharField(max_length=2)  # IE, SN, TF, JP
    # 题目方向：在对应维度上更偏向哪个极性（例如IE中的I或E）
    keyed_pole = models.CharField(max_length=1, default="I")
    weight = models.IntegerField(default=1)
    order = models.IntegerField(default=0)
    active = models.BooleanField(default=True)
    questionnaire = models.ForeignKey(
        Questionnaire, on_delete=models.CASCADE, related_name="questions", null=True, blank=True
    )

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['dimension', 'active']),
            models.Index(fields=['questionnaire', 'active']),
        ]

    def clean(self):
        """验证模型数据"""
        super().clean()
        
        # 验证维度
        if self.dimension not in self.DIMENSIONS:
            raise ValidationError(f'维度必须是 {list(self.DIMENSIONS.keys())} 之一')
        
        # 验证keyed_pole是否属于对应维度
        valid_poles = self.DIMENSIONS.get(self.dimension, ())
        if self.keyed_pole not in valid_poles:
            raise ValidationError(
                f'维度 {self.dimension} 的 keyed_pole 必须是 {valid_poles} 之一'
            )
        
        # 验证weight范围
        if self.weight < 1:
            raise ValidationError('weight 必须大于等于 1')

    def save(self, *args, **kwargs):
        """保存前执行验证"""
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.text


class Response(models.Model):
    """用户回答模型"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice = models.IntegerField()  # 1..5 Likert
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "question")
        indexes = [
            models.Index(fields=['user', 'questionnaire']),
        ]

    def clean(self):
        """验证答案范围"""
        super().clean()
        # 根据问卷类型验证答案范围
        if self.questionnaire and self.questionnaire.key == 'mbti_standard_93':
            # 标准MBTI：1-2
            if not (1 <= self.choice <= 2):
                raise ValidationError('choice 必须在 1 到 2 之间（标准MBTI）')
        else:
            # 其他：1-5
            if not (1 <= self.choice <= 5):
                raise ValidationError('choice 必须在 1 到 5 之间')

    def save(self, *args, **kwargs):
        """保存前执行验证"""
        self.full_clean()
        super().save(*args, **kwargs)


class Result(models.Model):
    """测试结果模型"""
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    type_code = models.CharField(max_length=4)  # e.g., INTP
    score_detail = models.JSONField(default=dict)
    confidence = models.JSONField(default=dict)  # 每个维度的置信度(0..1)
    questionnaire = models.ForeignKey(Questionnaire, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['type_code']),
            models.Index(fields=['created_at']),
        ]

    def clean(self):
        """验证类型码格式"""
        super().clean()
        if len(self.type_code) != 4:
            raise ValidationError('type_code 必须是4个字符')
        valid_letters = {'I', 'E', 'S', 'N', 'T', 'F', 'J', 'P'}
        if not all(c in valid_letters for c in self.type_code):
            raise ValidationError(f'type_code 只能包含 {valid_letters} 中的字符')


class TypeProfile(models.Model):
    code = models.CharField(max_length=4, unique=True)  # 16类类型码
    name = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    strengths = models.TextField(blank=True)
    growth = models.TextField(blank=True)
    
    # 新增多维度分析字段
    personality_traits = models.TextField(blank=True, verbose_name="性格特点")
    work_style = models.TextField(blank=True, verbose_name="工作风格")
    interpersonal_relations = models.TextField(blank=True, verbose_name="人际关系")
    emotional_expression = models.TextField(blank=True, verbose_name="情感表达")
    decision_making = models.TextField(blank=True, verbose_name="决策方式")
    stress_management = models.TextField(blank=True, verbose_name="压力管理")
    learning_style = models.TextField(blank=True, verbose_name="学习方式")
    career_suggestions = models.TextField(blank=True, verbose_name="职业建议")
    life_philosophy = models.TextField(blank=True, verbose_name="生活哲学")
    communication_style = models.TextField(blank=True, verbose_name="沟通风格")

    def __str__(self):
        return self.code