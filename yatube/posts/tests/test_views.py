from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='test_user_author')
        cls.follower = User.objects.create_user(username='test_follower')
        cls.not_follower = User.objects.create_user(username='test_nofollower')
        cls.group = Group.objects.create(
            title='null-groupe',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.null_group = Group.objects.create(
            title='Пустая группа',
            slug='null-slug',
            description='Тестовое описание',
        )
        post_objects = [
            Post(
                author=cls.user_author,
                text='Тестовый пост ' + str(i),
                group=cls.group,
                image='posts/1.png'
            )
            for i in range(settings.PER_PAGE + 2)
        ]
        Post.objects.bulk_create(post_objects)
        cls.post = Post.objects.first()
        cls.count_objects_on_last_page = len(post_objects) % settings.PER_PAGE

    def setUp(self):
        self.authorized_client_author = Client()
        self.authorized_client_author.force_login(self.user_author)
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)
        self.authorized_not_follower = Client()
        self.authorized_not_follower.force_login(self.not_follower)

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        posts_index_url = reverse('posts:index')
        posts_create_url = reverse('posts:post_create')
        posts_group_list_url = reverse(
            'posts:group_list', args={self.group.slug}
        )
        posts_profile_url = reverse(
            'posts:profile', args={self.user_author}
        )
        posts_post_detail_url = reverse(
            'posts:post_detail', args={self.post.id}
        )
        posts_post_edit_url = reverse(
            'posts:post_edit', args={self.post.id}
        )
        templates_page_names = {
            posts_index_url: 'posts/index.html',
            posts_create_url: 'posts/create_post.html',
            posts_group_list_url: 'posts/group_list.html',
            posts_profile_url: 'posts/profile.html',
            posts_post_detail_url: 'posts/post_detail.html',
            posts_post_edit_url: 'posts/create_post.html'
        }
        for reverse_name, template in templates_page_names.items():
            with self.subTest(reverse_name=reverse_name, template=template):
                response = self.authorized_client_author.get(reverse_name)
                self.assertTemplateUsed(
                    response, template,
                    msg_prefix=f'Для {reverse_name}'
                               f' не используется шаблон {template}')

    def test_index_uses_correct_context(self):
        response = self.authorized_client_author.get(reverse('posts:index'))
        self.assertIn('page_obj', response.context)

    def test_pagination_index_pages(self):
        response = self.authorized_client_author.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), settings.PER_PAGE)
        response = self.client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(
            len(response.context['page_obj']), self.count_objects_on_last_page
        )

    def test_group_list_uses_correct_context(self):
        response = self.authorized_client_author.get(
            reverse('posts:group_list', args={self.group.slug})
        )
        self.assertEqual(response.context['group'], self.group)
        self.assertIn('page_obj', response.context)

    def test_pagitation_group_list_pages(self):
        response = self.authorized_client_author.get(
            reverse('posts:group_list', args={self.group.slug})
        )
        self.assertEqual(len(response.context['page_obj']), settings.PER_PAGE)
        response = self.authorized_client_author.get(
            reverse('posts:group_list', args={self.group.slug}) + '?page=2'
        )
        self.assertEqual(
            len(response.context['page_obj']), self.count_objects_on_last_page
        )

    def test_profile_uses_correct_context(self):
        response = self.authorized_client_author.get(
            reverse('posts:profile', args={self.user_author})
        )
        self.assertIn('author', response.context)
        self.assertIn('page_obj', response.context)
        self.assertEqual(
            response.context['page_obj'][0].author, self.user_author
        )

    def test_pagination_profile_pages(self):
        response = self.authorized_client_author.get(
            reverse('posts:profile', args={self.user_author})
        )
        self.assertEqual(len(response.context['page_obj']), settings.PER_PAGE)
        response = self.authorized_client_author.get(
            reverse('posts:profile', args={self.user_author}) + '?page=2'
        )
        self.assertEqual(
            len(response.context['page_obj']), self.count_objects_on_last_page
        )

    def test_post_detail_uses_correct_context(self):
        response = self.authorized_client_author.get(
            reverse('posts:post_detail', args={self.post.id}))
        self.assertEqual(self.post, response.context['post'])
        self.assertEqual(response.context['count_post'], self.post.id)

    def test_post_edit_uses_correct_context(self):
        response = self.authorized_client_author.get(
            reverse('posts:post_edit', args={self.post.id})
        )
        text_inital = response.context.get('form').fields.get('text')
        group_inital = response.context.get('form').fields.get('group')
        self.assertIsInstance(text_inital, forms.fields.CharField)
        self.assertIsInstance(group_inital, forms.models.ModelChoiceField)
        self.assertEqual(response.context['post'].text, self.post.text)

    def test_post_create_uses_correct_context(self):
        response = self.authorized_client_author.get(
            reverse('posts:post_create')
        )
        text_inital = response.context.get('form').fields.get('text')
        group_inital = response.context.get('form').fields.get('group')
        self.assertIsInstance(text_inital, forms.fields.CharField)
        self.assertIsInstance(group_inital, forms.models.ModelChoiceField)

    def test_post_on_index_page(self):
        response = self.authorized_client_author.get(reverse('posts:index'))
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_post_on_group_page(self):
        response = self.authorized_client_author.get(
            reverse('posts:group_list', args={self.group.slug})
        )
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_post_on_profile_page(self):
        response = self.authorized_client_author.get(
            reverse('posts:profile', args={self.user_author})
        )
        self.assertEqual(response.context['page_obj'][0], self.post)

    def test_post_is_not_in_another_group(self):
        """Проверьте, что этот пост не попал в группу,
         для которой не был предназначен."""
        self.assertEqual(Post.objects.filter(group=self.null_group).count(), 0)

    def test_cache_index_page(self):
        index_page = reverse('posts:index')
        test_object1 = self.authorized_client_author.get(index_page).content
        Post.objects.first().delete()
        test_object2 = self.authorized_client_author.get(index_page).content
        self.assertEqual(test_object1, test_object2)
        cache.clear()
        test_object3 = self.authorized_client_author.get(index_page).content
        self.assertNotEqual(test_object1, test_object3)

    def test_new_post_displayed_on_follow_page_for_follower(self):
        self.authorized_follower.post(
            reverse('posts:profile_follow', args={self.user_author})
        )
        form_data = {
            'text': 'Пост для подписчиков',
            'group': self.group.id
        }
        self.authorized_client_author.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        follow_index_page = reverse('posts:follow_index')
        response = self.authorized_follower.post(follow_index_page)
        self.assertEqual(
            response.context['page_obj'][0], self.user_author.posts.first()
        )
        response = self.authorized_not_follower.post(follow_index_page)
        self.assertEqual(len(response.context['page_obj']), 0)
