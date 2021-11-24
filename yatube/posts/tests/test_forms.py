import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='test_user_author')
        cls.group = Group.objects.create(
            title='groupe',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            text='В ожидании НЛО',
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_author)
        self.guest_client = Client()

    def test_create_post(self):
        form_data = {
            'text': 'Тестовый пост №2',
            'group': self.group.id
        }
        current_count_posts = Post.objects.count()
        response = self.authorized_client_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )

        self.assertEqual(Post.objects.count(), current_count_posts + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(form_data['text'], Post.objects.first().text)
        self.assertEqual(form_data['group'], Group.objects.first().id)
        self.assertEqual(self.user_author, Post.objects.first().author)

    def test_edit_post(self):
        form_data = {
            'text': 'НЛО отредактировало пост'
        }
        self.authorized_client_author.post(
            reverse('posts:post_edit', args={self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(
            form_data['text'],
            Post.objects.get(pk=self.post.id).text
        )

    def test_not_authorized_cannot_create_post(self):
        form_data = {
            'text': 'Я не опубликуюсь из-за необходимости авторизации',
            'group': self.group.id
        }
        current_count_posts = Post.objects.count()
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), current_count_posts)
        next_page = reverse("posts:post_create")
        expected_url = (
            reverse('users:login') + f'?next={next_page}'
        )
        self.assertRedirects(response, expected_url)

    def test_create_post_with_image(self):
        current_count_posts = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестовый c картинкой',
            'group': self.group.id,
            'image': uploaded,
        }
        self.authorized_client_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), current_count_posts + 1)
        # Сразу проверим, что страницы отдают корректный контекст.
        img_in_db = Post.objects.first().image
        response = self.authorized_client_author.get(reverse('posts:index'))
        posts_index_url = reverse('posts:index')
        posts_profile_url = reverse(
            'posts:profile', args={self.user_author}
        )
        posts_group_list_url = reverse(
            'posts:group_list', args={self.group.slug}
        )
        posts_post_detail_url = reverse(
            'posts:post_detail', args={Post.objects.count()}
        )
        pages_name_with_expected_image = {
            posts_index_url: img_in_db,
            posts_profile_url: img_in_db,
            posts_group_list_url: img_in_db,
        }

        for reverse_name, image in pages_name_with_expected_image.items():
            with self.subTest(reverse_name=reverse_name, image=image):
                response = self.authorized_client_author.get(reverse_name)
                self.assertEqual(
                    response.context['page_obj'][0].image, img_in_db,
                    f'на странице {reverse_name} в контексте нет {image}'
                )
        response = self.authorized_client_author.get(posts_post_detail_url)
        self.assertEqual(
            response.context['post'].image, img_in_db,
            f'на странице {posts_post_detail_url} в контексте нет {img_in_db}'
        )

    def test_not_authorized_cannot_comment_post(self):
        form_data = {
            'text': 'Я не опубликуюсь из-за необходимости авторизации',
        }
        current_count_comments = Comment.objects.count()
        response = self.guest_client.post(
            reverse('posts:add_comment', args={self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), current_count_comments)
        next_page = reverse('posts:add_comment', args={self.post.id})
        expected_redirect_url = (
            reverse('users:login') + f'?next={next_page}'
        )
        self.assertRedirects(response, expected_redirect_url)

    def test_comment_is_added(self):
        current_count_comments = Comment.objects.count()
        form_data = {
            'text': 'кг/ам',
        }
        self.authorized_client_author.post(
            reverse('posts:add_comment', args={self.post.id}),
            data=form_data,
            follow=True
        )
        response = self.authorized_client_author.post(
            reverse('posts:post_detail', args={self.post.id})
        )
        self.assertEqual(
            response.context['comments'][0].text, form_data['text']
        )
        self.assertEqual(Comment.objects.count(), current_count_comments + 1)
