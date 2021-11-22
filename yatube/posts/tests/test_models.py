from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем, что у моделей корректно работает __str__."""
        post = PostModelTest.post
        expected_post_text = post.text
        group = PostModelTest.group
        expected_group_title = group.title
        objects_expected_names = {
            post: expected_post_text,
            group: expected_group_title
        }
        for model, expected_value in objects_expected_names.items():
            with self.subTest(model=model, expected_value=expected_value):
                self.assertEqual(
                    expected_value, str(model),
                    f'Модель {model} не возвращает self.text'
                )

    def test_verbose_name_post(self):
        post = PostModelTest.post
        field_verboses = {
            'author': 'Автор',
            'group': 'Группа'
        }
        for field, expected_value in field_verboses.items():
            with self.subTest(field=field, expected_value=expected_value):
                self.assertEqual(
                    post._meta.get_field(field).verbose_name, expected_value)

    def test_help_text_post(self):
        post = PostModelTest.post
        field_help_texts = {
            'text': 'Введите текст поста',
            'group': 'Выберите группу'
        }
        for field, expected_value in field_help_texts.items():
            with self.subTest(field=field, expected_value=expected_value):
                self.assertEqual(
                    post._meta.get_field(field).help_text, expected_value)
