from rest_framework import serializers
from activity.models import StudentQuestion
import re
from django.utils import timezone

class StudentQuestionSerializer(serializers.ModelSerializer):
    activity_name = serializers.CharField(source='activity.activity_name', read_only=True)
    question_text = serializers.CharField(source='activity_question.question_text', read_only=True)
    quiz_type = serializers.StringRelatedField(source='activity_question.quiz_type', read_only=True)
    max_score = serializers.FloatField(source='activity_question.score', read_only=True)
    is_correct = serializers.SerializerMethodField()
    points_earned = serializers.SerializerMethodField()
    
    class Meta:
        model = StudentQuestion
        fields = [
            'id', 'student', 'activity', 
            'activity_name', 'question_text', 'quiz_type',
            'student_answer', 'max_score',
            'is_correct', 'points_earned', 'score',
            'submission_time', 'is_participation',
            'uploaded_file'
        ]
        read_only_fields = ['id', 'student', 'activity', 'submission_time', 'score']
    
    def normalize_text(self, text):
        """Normalize text for comparison"""
        if not text:
            return ''
        return re.sub(r'\W+', '', str(text).lower())
    
    def get_is_correct(self, obj):
        """Determine if the student's answer is correct (internal only)"""
        if not obj.student_answer or not obj.activity_question.correct_answer:
            return False
            
        quiz_type = obj.activity_question.quiz_type.name if obj.activity_question.quiz_type else ''
        
        # Handle different question types
        if quiz_type == 'Matching Type':
            return self._validate_matching_answer(obj)
        elif quiz_type in ['Multiple Choice', 'True/False', 'Fill in the Blank', 'Calculated Numeric']:
            return self._validate_exact_match(obj)
        elif quiz_type == 'Essay':
            return False  # Essays require manual grading
        elif quiz_type == 'Document':
            return False  # Documents require manual review
        else:
            return False
    
    def _validate_exact_match(self, obj):
        """Validate exact match answers"""
        student_normalized = self.normalize_text(obj.student_answer)
        correct_normalized = self.normalize_text(obj.activity_question.correct_answer)
        return student_normalized == correct_normalized
    
    def _validate_matching_answer(self, obj):
        """Validate matching type answers"""
        try:
            # Parse the matching pairs from both student and correct answers
            student_pairs = self._parse_matching_pairs(obj.student_answer)
            correct_pairs = self._parse_matching_pairs(obj.activity_question.correct_answer)
            
            # Normalize and compare
            student_normalized = [(self.normalize_text(left), self.normalize_text(right)) for left, right in student_pairs]
            correct_normalized = [(self.normalize_text(left), self.normalize_text(right)) for left, right in correct_pairs]
            
            return student_normalized == correct_normalized
        except:
            return False
    
    def _parse_matching_pairs(self, answer_text):
        """Parse matching pairs from answer text"""
        if not answer_text:
            return []
        
        pairs = []
        # Handle both string and list formats
        if '->' in str(answer_text):
            # String format: "left1 -> right1, left2 -> right2"
            pairs_str = str(answer_text).split(',')
            for pair in pairs_str:
                if '->' in pair:
                    left, right = pair.split('->', 1)
                    pairs.append((left.strip(), right.strip()))
        else:
            # List format: "[('left1', 'right1'), ('left2', 'right2')]"
            try:
                import ast
                pairs = ast.literal_eval(str(answer_text))
                if isinstance(pairs, list):
                    pairs = [(str(left), str(right)) for left, right in pairs]
            except:
                pairs = []
        return pairs
    
    def get_points_earned(self, obj):
        """Calculate points earned based on correctness"""
        if self.get_is_correct(obj):
            return obj.activity_question.score or 0
        return 0
    
    def validate(self, data):
        # Auto-calculate score based on correctness
        if 'student_answer' in data and self.instance:
            quiz_type = self.instance.activity_question.quiz_type.name if self.instance.activity_question.quiz_type else ''
            
            if quiz_type in ['Multiple Choice', 'True/False', 'Fill in the Blank', 'Calculated Numeric', 'Matching Type']:
                is_correct = self.get_is_correct(self.instance)
                data['score'] = self.instance.activity_question.score if is_correct else 0
            elif quiz_type in ['Essay', 'Document']:
                # Keep existing score for manual grading
                data['score'] = data.get('score', self.instance.score or 0)
        
        return data
    
    def create(self, validated_data):
        validated_data['submission_time'] = timezone.now()
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        validated_data['submission_time'] = timezone.now()
        
        # Auto-calculate score on update
        quiz_type = instance.activity_question.quiz_type.name if instance.activity_question.quiz_type else ''
        
        if quiz_type in ['Multiple Choice', 'True/False', 'Fill in the Blank', 'Calculated Numeric', 'Matching Type']:
            instance.student_answer = validated_data.get('student_answer', instance.student_answer)
            validated_data['score'] = self.get_points_earned(instance)
        
        return super().update(instance, validated_data)