"""reddit"""

import json
import mechanize
import base64
import requests
from urllib.parse import urlencode

vote_url = 'http://www.reddit.com/api/vote/'
vote_post_string = 'id=%s&dir=%s&r=%s&uh=%s'


class RedditThing(object):

    ups = 0
    downs = 0

    def __init__(self, json_data, reddit_agent=None):

        self._agent = reddit_agent
        self._data = json_data.get("data", {})

        for key, value in self._data.items():
            setattr(self, key, value)
    
    def set_vote(self, direction):
        vote_response = self._agent.set_vote(self.name, self.subreddit, direction)
        self._last_vote_response = vote_response

    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"RedditThing<%s> by %s" % (self.name, self.author)


class RedditT5(RedditThing):

    def __init__(self, json_data, reddit_agent=None):

        self._kind = json_data.get("kind", "t5")
        super(RedditT5, self).__init__(json_data, reddit_agent)

    def get_as_subreddit(self):
        display_name = self.display_name
        return self._agent.get_subreddit(display_name)

    def __unicode__(self):
        return u"RedditT5<%s>" % (self.display_name)


class RedditComment(RedditThing):

    ups = 0
    downs = 0

    def __init__(self, json_data, reddit_agent=None):

        self._kind = json_data.get("kind", "t1")
        self._replies = None
        super(RedditComment, self).__init__(json_data, reddit_agent)
    
    def get_replies(self):

        if self._replies:
            return self._replies

        try:
            children = self._data.get("replies", {}).get("data", {}).get("children", [])
        except:
            # add logging
            print(e)
            return []
        replies = []

        for item in children:
            kind = item.get("kind", None)
            if kind == "t1":
                try:
                    replies.append(RedditComment(item, self._agent))
                except:
                    # add logging?
                    pass
        self._replies = replies
        return replies

    def get_thread(self):
        return self._agent.get_permalinked_thread(self.name, self.permalink)

    def __unicode__(self):
        return u"RedditComment<%s> by %s" % (self.name, self.author)

    
class RedditPost(RedditThing):

    ups = 0
    downs = 0

    def __init__(self, json_data, reddit_agent=None):

        self._kind = json_data.get("kind", "t3")
        super(RedditPost, self).__init__(json_data, reddit_agent)
    
    def get_thread(self):
        return self._agent.get_permalinked_thread(self.name, self.permalink)

    def __unicode__(self):
        return u"RedditPost<%s> by %s" % (self.name, self.author)


class RedditListing(RedditThing):

    def __init__(self, name, json_data, reddit_agent=None):

        self._name = name
        self._posts = None
        super(RedditListing, self).__init__(json_data, reddit_agent)

        for key, value in self._data.items():
            setattr(self, key, value)

    def get_posts(self):

        if self._posts:
            return self._posts

        children = self.children
        posts = []
        for item in children:
            kind = item.get("kind", None)
            if kind == "t3":
                try:
                    posts.append(RedditPost(item, self._agent))
                except:
                    # add logging?
                    pass
        self._posts = posts
        return posts

    def get_last_post(self):
        try:
            return self.get_posts()[-1]
        except IndexError:
            return None

    def __unicode__(self):
        return u"RedditListing<%s>" % (self._name.title())


class RedditSubredditList(RedditListing):
    
    def __init__(self, json_data, reddit_agent=None):

        self._subreddits = None
        super(RedditSubredditList, self).__init__("List of reddits", json_data, reddit_agent)

        for key, value in self._data.items():
            setattr(self, key, value)

    def get_subreddits(self):
        
        if self._subreddits:
            return self._subreddits

        children = self.children
        subreddits = []
        for item in children:
            kind = item.get("kind", None)
            if kind == "t5":
                try:
                    subreddits.append(RedditT5(item, self._agent))
                except:
                    #add logging?
                    pass
        self._subreddits = subreddits
        return subreddits

    def get_next_page(self):

        last_subreddit = self.get_subreddits()[-1]
        last_subreddit_name = last_subreddit.name

        return self._agent.get_subreddit_listing(after=last_subreddit_name)


class RedditSubreddit(RedditListing):

    _url = "https://oauth.reddit.com/r/%s%s/.json"
    
    def __init__(self, subreddit, json_data, reddit_agent=None, ordering=None):

        self.subreddit = subreddit
        self._kind = json_data.get("kind", "t2")
        self._ordering = ordering
        super(RedditSubreddit, self).__init__(subreddit, json_data, reddit_agent)

    def get_next_page(self):

        last_post = self.get_last_post()
        last_post_name = last_post.name
        ordering = self._ordering

        return self._agent.get_subreddit(self.subreddit, after=last_post_name, ordering=ordering)

    def __unicode__(self):
        return u"RedditSubreddit<%s>" % (self.subreddit.title())


class RedditThread(RedditThing):

    _url = "https://oauth.reddit.com/r/%s/comments/%s.json"

    def __init__(self, name, json_data, reddit_agent=None):

        self.name = name
        self._kind = json_data.get("kind", "t1")
        self._replies = None

        post_data = json_data[1]['data']['children'][0]
        self.post = RedditPost(post_data, reddit_agent)

        self._reply_data = json_data[1]['data']['children']
        super(RedditThread, self).__init__(post_data, reddit_agent)
    
    def set_vote(self, direction):
        vote_response = self.post.set_vote(direction)
        self._last_vote_response = vote_response

    def get_replies(self):

        if self._replies:
            return self._replies

        try:
            children = self._reply_data
        except:
            #add logging
            return []
        replies = []

        for item in children:
            kind = item.get("kind", None)
            if kind == "t1":
                try:
                    a_reply = RedditComment(item, self._agent)
                    a_reply.permalink = "%s%s" % (self.post.permalink, a_reply.id)
                    replies.append(a_reply)
                except:
                    # add logging?
                    pass
        self._replies = replies
        return replies
    
    def get_all_replies(self, reply=None, replies=None):
        if replies == None:
            replies = set()
        
        if reply == None:
            target = self
        else:
            target = reply

        target_replies = target.get_replies()
        for target_reply in target_replies:

            replies.update(self.get_all_replies(reply=target_reply, replies=replies))
            replies.add(target_reply)
        
        replies.add(target)
        return replies

    def __unicode__(self):
        return u"RedditThread<%s>" % (self.name.title())


class RedditUserInfo(RedditThing):

    _url = "https://oauth.reddit.com/api/v1/user/%s/about"

    def __init__(self, json_data, reddit_agent=None):

        self._kind = json_data.get("kind", "t2")
        super(RedditUserInfo, self).__init__(json_data, reddit_agent)

    def __unicode__(self):
        return u"RedditUserInfo<%s>" % (self.name)


class RedditUserPage(RedditListing):

    _url = "https://oauth.reddit.com/user/%s.json"
    
    def __init__(self, username, json_data, reddit_agent=None, section=None):

        self.username = username
        self._kind = json_data.get("kind", "t2")
        self._comments = None
        self._section = section if section else "overview"
    
        super(RedditUserPage, self).__init__(username, json_data, reddit_agent)

    def get_user_info(self):
        return self._agent.get_user_info(self.username)

    def get_comments(self):

        if self._comments:
            return self._comments

        #No comments in this section
        if self._section == "submitted":
            self._comments = []
            return self._comments

        children = self._data.get("children", {})
        comments = []

        for item in children:
            kind = item.get("kind", None)
            if kind == "t1":
                try:
                    comments.append(RedditComment(item, self._agent))
                except:
                    # add logging?
                    pass
        self._comments = comments
        return comments

    def get_posts(self):

        if self._section == "comments":
            if self._posts:
                return self._posts
            else:
                self._posts = []
                return self._posts
        else:
            return super(RedditUserPage, self).get_posts()

    def get_last_comment(self):
        try:
            return self.get_comments()[-1]
        except IndexError:
            return None

    def get_last_item(self):

        last_post = self.get_last_post()
        last_comment = self.get_last_comment()

        if last_post == None:
            return last_comment
        if last_comment == None:
            return last_post
        
        #if self.filter == "newest"
        if last_post.created < last_comment.created:
            return last_post
        else:
            return last_comment

    def get_next_page(self):

        try:
            last_item = self.get_last_item()

            if not last_item:
                return None

            last_item_name = last_item.name

            return self._agent.get_user_page(self.username, after=last_item_name)
        except Exception as e:
            #add logging?
            print(e)
            return None

    def __unicode__(self):
        return u"RedditUserPage<%s>" % (self.username.title())


class RedditSession(object):

    _opener = None
    _username = 'a_test_account'
    _password = 'a_test_password'
    _client_id = None
    _client_secret = None

    _login_url = 'https://www.reddit.com/api/v1/access_token'
    
    _last_modhash = ''

    def __init__(self, **kwargs):
        self._username = str(kwargs.get('user', RedditSession._username))
        self._password = str(kwargs.get('passwd', RedditSession._password))
        self._client_id = str(kwargs.get('client_id', RedditSession._client_id))
        self._client_secret = str(kwargs.get('client_secret', RedditSession._client_secret))
        
        if not self._client_id or not self._client_secret:
            raise Exception("Reddit API 클라이언트 ID와 시크릿이 필요합니다.")

        self._opener = mechanize.Browser()
        self._opener.set_handle_robots(False)
        self._access_token = None
        self._do_login()

    def _do_login(self):
        try:
            print(f"로그인 시도: {self._username}")
            print(f"클라이언트 ID: {self._client_id}")
            
            # Basic 인증 헤더 생성
            auth = base64.b64encode(f"{self._client_id}:{self._client_secret}".encode()).decode()
            headers = {
                'User-Agent': 'MyRedditApp/1.0 (by /u/sidaein)',
                'Authorization': f'Basic {auth}',
                'Content-Type': 'application/x-www-form-urlencoded'
            }
            
            # POST 데이터 준비
            data = {
                'grant_type': 'password',
                'username': self._username,
                'password': self._password,
                'scope': 'read identity'
            }
            
            print(f"요청 URL: {self._login_url}")
            print(f"요청 헤더: {headers}")
            print(f"POST 데이터: {data}")
            
            # requests를 사용하여 로그인 요청
            response = requests.post(
                self._login_url,
                headers=headers,
                data=urlencode(data),
                timeout=30
            )
            
            print(f"응답 상태 코드: {response.status_code}")
            print(f"응답 헤더: {response.headers}")
            print(f"응답 데이터: {response.text}")
            
            if response.status_code == 200:
                login_response = response.json()
                if 'access_token' in login_response:
                    self._access_token = login_response['access_token']
                    self._opener.addheaders = [
                        ('User-Agent', 'MyRedditApp/1.0 (by /u/sidaein)'),
                        ('Authorization', f'Bearer {self._access_token}')
                    ]
                    print("로그인 성공!")
                else:
                    error_msg = login_response.get('error', '알 수 없는 오류')
                    raise Exception(f"액세스 토큰을 받지 못했습니다: {error_msg}")
            else:
                error_msg = response.json().get('error', '알 수 없는 오류')
                raise Exception(f"로그인 실패: {error_msg}")
                
        except Exception as e:
            print(f"로그인 중 에러 발생: {str(e)}")
            raise

    def make_request(self, url, post=None, reqtype=None):
        try:
            print(f"요청 URL: {url}")
            print(f"요청 헤더: {self._opener.addheaders}")
            
            # requests를 사용하여 API 요청
            headers = dict(self._opener.addheaders)
            if post:
                print(f"POST 데이터: {post}")
                response = requests.post(url, headers=headers, data=post)
            else:
                response = requests.get(url, headers=headers)
            
            print(f"응답 상태 코드: {response.status_code}")
            print(f"응답 데이터: {response.text}")
            
            if response.status_code == 200:
                return response.json()
            else:
                raise Exception(f"API 요청 실패: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"요청 중 에러 발생: {str(e)}")
            raise

    def __unicode__(self):
        return u"RedditSession<%s> %s" % (self._access_token, self._username)


class RedditAgent(object):

    _after_pattern = "?after=%s"
    _user_info_cache = {}
    
    def __init__(self, reddit_session):
        
        self._session = reddit_session
        self._username = reddit_session._username

    def set_vote(self, name, subreddit, direction):
        
        modhash = self._session._access_token
        vote_request = vote_post_string % (name, direction, subreddit, modhash)
        vote_response = self._session.make_request(vote_url, vote_request, reqtype="vote")

        self._last_vote_response = vote_response

        return vote_response

    def get_subreddit(self, subreddit, after=None, ordering=None):

        if ordering:
            order_tag = "/%s" % ordering
        else:
            order_tag = None

        url = RedditSubreddit._url % (subreddit, order_tag or '')

        if after:
            url = "%s%s" % (url, self._after_pattern % (after,),)

        data = self._session.make_request(url, reqtype="basic_info")

        if data:
            return RedditSubreddit(subreddit, data, self, ordering=ordering)

    def get_subreddit_listing(self, after=None):

        url = "http://www.reddit.com/reddits.json"

        if after:
            url = "%s%s" % (url, "?after=%s" % after)
        
        print(url)
        data = self._session.make_request(url, reqtype="subreddit_listing")

        if data:
            return RedditSubredditList(data, self)

    def get_thread(self, subreddit, name, after=None):

        url = RedditThread._url % (subreddit, name)

        if after:
            url = "%s%s" % (url, self._after_pattern % (after,),)
        
        data = self._session.make_request(url, reqtype="thread")

        if data:
            return RedditThread(name, data, self)
    
    def get_permalinked_thread(self, name, permalink, after=None):
        
        url = "http://www.reddit.com%s.json" % permalink
                
        if after:
            url = "%s%s" % (url, self._after_pattern % (after,),)

        data = self._session.make_request(url, reqtype="permalink_thread")

        if data:
            return RedditThread(name, data, self)

    def get_user_info(self, username, update=True):

        if username not in self._user_info_cache or update:
            data = self._session.make_request(RedditUserInfo._url % username, reqtype="basic_info")
            if data:
                user = RedditUserInfo(data, self)
            else:
                user = None
            self._user_info_cache[username] = user
        else:
            user = self._user_info_cache[username]
        
        return user

    def get_user_page(self, username, after=None):

        url = RedditUserPage._url % username

        if after:
            url = "%s%s" % (url, self._after_pattern % (after,),)

        data = self._session.make_request(url, reqtype="user_page")

        if data:
            return RedditUserPage(username, data, self)

    def get_my_user_page(self, after=None):

        if self._username:
            return self.get_user_page(self.username, after=after)

    def get_my_user_info(self):

        if self._username:
            return self.get_user_info(self.username)


class RedditUser(RedditSession):

    def __init__(self, **kwargs):
        super(RedditUser, self).__init__(**kwargs)
        self._user_url = 'https://oauth.reddit.com/user/%s/about.json'
        self._user_info = self.make_request(self._user_url % self._username)
        self._last_modhash = self._user_info['data']['modhash']
        self.username = self._username
        self.upvotees = {}
        self.downvotees = {}
        self.recent_scans = {}

    def get_my_user_info(self):
        """현재 로그인한 사용자의 정보를 반환합니다."""
        try:
            response = self.make_request(self._user_url % self._username)
            if response and 'data' in response:
                return UserInfo(response['data'])
            raise Exception("사용자 정보를 가져오는데 실패했습니다.")
        except Exception as e:
            print(f"사용자 정보 조회 중 에러 발생: {str(e)}")
            raise

    def get_subreddit(self, subreddit_name):
        """서브레딧 정보를 가져옵니다."""
        try:
            url = f'https://oauth.reddit.com/r/{subreddit_name}/hot.json'
            response = self.make_request(url)
            if response and 'data' in response:
                return Subreddit(response['data'], self)
            raise Exception("서브레딧 정보를 가져오는데 실패했습니다.")
        except Exception as e:
            print(f"서브레딧 정보 조회 중 에러 발생: {str(e)}")
            raise

    def add_upvotee(self, username=None, userobj=None):
        pass

    def add_downvotee(self, username=None, userobj=None):
        pass

    def scan_user_for_unvoted_items(self, username=None, limit=5, posts=True, comments=True):

        if username in self.recent_scans:
            unvoted_comments, unvoted_posts = self.recent_scans[username]
            items = set()
            items.update(unvoted_posts)
            items.update(unvoted_comments)
            return items

        user_page = self.get_user_page(username)
        pages = []
        page_number = 0
        while user_page and page_number < limit:
            pages.append(user_page)
            print("current page: %s" % (user_page))
            user_page = user_page.get_next_page()
            page_number = page_number + 1
            print("page#: %s limit: %s" % (page_number, limit))
    
        unvoted_comments = []
        unvoted_posts = []

        for page in pages:
            for post in page.get_posts():
                if post.likes == None:
                    unvoted_posts.append(post)
            for comment in page.get_comments():
                if comment.likes == None:
                    unvoted_comments.append(comment)
        unvoted_comments = set(unvoted_comments)
        unvoted_posts = set(unvoted_posts)
        items = set()
        items.update(unvoted_posts)
        items.update(unvoted_comments)
        self.recent_scans[username] = (unvoted_comments, unvoted_posts)

        return  items


class UserInfo:
    """Reddit 사용자 정보를 담는 클래스"""
    def __init__(self, data):
        self.name = data.get('name', '')
        self.created_utc = data.get('created_utc', 0)
        self.link_karma = data.get('link_karma', 0)
        self.comment_karma = data.get('comment_karma', 0)
        self.total_karma = data.get('total_karma', 0)
        self.is_gold = data.get('is_gold', False)
        self.is_mod = data.get('is_mod', False)
        self.has_verified_email = data.get('has_verified_email', False)
        self.id = data.get('id', '')
        self.over_18 = data.get('over_18', False)
        self.icon_img = data.get('icon_img', '')
        self.pref_nightmode = data.get('pref_nightmode', False)
        self.inbox_count = data.get('inbox_count', 0)
        self.has_subscribed = data.get('has_subscribed', False)


class Subreddit:
    """Reddit 서브레딧 정보를 담는 클래스"""
    def __init__(self, data, reddit_session):
        self.data = data
        self.reddit = reddit_session
        self.children = data.get('children', [])
        self.after = data.get('after')
        self.before = data.get('before')

    def get_posts(self, limit=10):
        """서브레딧의 게시글을 가져옵니다."""
        posts = []
        for child in self.children[:limit]:
            post_data = child.get('data', {})
            posts.append(Post(post_data))
        return posts


class Post:
    """Reddit 게시글 정보를 담는 클래스"""
    def __init__(self, data):
        self.title = data.get('title', '')
        self.author = data.get('author', '')
        self.score = data.get('score', 0)
        self.num_comments = data.get('num_comments', 0)
        self.url = data.get('url', '')
        self.permalink = data.get('permalink', '')
        self.created_utc = data.get('created_utc', 0)
        self.selftext = data.get('selftext', '')
        self.id = data.get('id', '')
        self.subreddit = data.get('subreddit', '')
