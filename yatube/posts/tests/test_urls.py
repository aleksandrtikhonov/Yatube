from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='test_user_author')
        cls.user_non_author = User.objects.create_user(
            username='test_user_non_author'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            text='Тестовая группа',
        )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_author)
        self.authorized_non_author = Client()
        self.authorized_non_author.force_login(self.user_non_author)

    def test_public_urls_responce_status_code(self):
        """Проверка страниц доступных для любого пользователя"""
        urls_expected_codes = {
            '/': HTTPStatus.OK,
            '/profile/test_user_author/': HTTPStatus.OK,
            '/posts/1/': HTTPStatus.OK,
            '/unexisting_page': HTTPStatus.NOT_FOUND
        }

        for url, expected_code in urls_expected_codes.items():
            with self.subTest(url=url, expected_code=expected_code):
                response = self.guest_client.get(url)
                self.assertEqual(
                    response.status_code, expected_code,
                    f'ошибка при проверке {url}, '
                    f'ожидается код ответа HTTP {expected_code}, '
                    f'возвращается {response.status_code}'
                )

    def test_not_authorized_can_edit_post(self):
        """Проверка редиректа анонимного
        пользвателя при попытке редактирования поста"""
        url = '/posts/1/edit/'
        response = self.guest_client.get(url, follow=True)
        self.assertRedirects(
            response, '/auth/login/?next=/posts/1/edit/',
            msg_prefix='Проверьте редактирование поста '
            'для анонимного пользователя')

    def test_not_author_cannot_edit_post(self):
        """Проверка редиректа не автора поста
        при попытке редактирования поста"""
        url = '/posts/1/edit/'
        response = self.authorized_non_author.get(url, follow=True)
        self.assertRedirects(
            response, '/posts/1/',
            msg_prefix='Проверьте редактирование поста не для автора')

    def test_authorized_can_create_post(self):
        """Проверка возможности создания поста авторизованным пользователем"""
        url = '/create/'
        response = self.authorized_non_author.get(url)
        self.assertEqual(
            response.status_code, HTTPStatus.OK,
            'Проверьте, что пользователь может создать пост')

    def test_author_can_edit_post(self):
        """Проверка возможности радактирования поста автором"""
        url = '/posts/1/edit/'
        response = self.authorized_client_author.get(url)
        self.assertEqual(
            response.status_code, HTTPStatus.OK,
            'Проверьте, что автр поста может редактировать свой пост')

    def test_urls_uses_correct_template(self):
        """Проверка соотвествия вызываемых шаблонов
        для каждого адреса"""
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/test_user_author/': 'posts/profile.html',
            '/posts/1/': 'posts/post_detail.html',
            '/posts/1/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html'
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url, template=template):
                response = self.authorized_client_author.get(url)
                self.assertTemplateUsed(
                    response, template,
                    msg_prefix=f'Для {url} не используется шаблон  {template}')

    def test_user_can_use_follow_service(self):
        self.authorized_non_author.post(
            reverse('posts:profile_follow', args={self.user_author})
        )
        expected_author = self.user_non_author.follower.first().author
        self.assertEqual(self.user_author, expected_author)
        self.authorized_non_author.post(
            reverse('posts:profile_unfollow', args={self.user_author})
        )
        self.assertIsNone(self.user_non_author.follower.first())
