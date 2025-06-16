import os
from dotenv import load_dotenv
from pyreddit.core import RedditUser

def check_login_status(reddit):
    try:
        # 사용자 정보 가져오기
        user_info = reddit.get_my_user_info()
        print("\n=== 로그인 상태 확인 ===")
        print(f"로그인 성공!")
        print(f"사용자 이름: {user_info.name}")
        print(f"계정 생성일: {user_info.created_utc}")
        print(f"카르마: {user_info.link_karma} (링크) / {user_info.comment_karma} (댓글)")
        return True
    except Exception as e:
        print("\n=== 로그인 상태 확인 ===")
        print(f"로그인 실패: {str(e)}")
        return False

def main():
    try:
        # .env 파일 로드
        load_dotenv()
        
        # .env 파일에서 Reddit 계정 정보 가져오기
        username = os.getenv('REDDIT_USERNAME')
        password = os.getenv('REDDIT_PASSWORD')
        client_id = os.getenv('REDDIT_CLIENT_ID')
        client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        
        if not all([username, password, client_id, client_secret]):
            print("계정 정보가 설정되지 않았습니다.")
            print("프로젝트 루트 디렉토리에 .env 파일을 생성하고 다음 내용을 입력하세요:")
            print("REDDIT_USERNAME=your_username")
            print("REDDIT_PASSWORD=your_password")
            print("REDDIT_CLIENT_ID=your_client_id")
            print("REDDIT_CLIENT_SECRET=your_client_secret")
            return

        # Reddit 계정으로 로그인
        reddit = RedditUser(
            user=username,  # username 대신 user 사용
            passwd=password,  # password 대신 passwd 사용
            client_id=client_id,
            client_secret=client_secret
        )
        
        # 로그인 상태 확인
        if not check_login_status(reddit):
            return
        
        # Python 서브레딧 가져오기
        subreddit = reddit.get_subreddit('python')
        posts = subreddit.get_posts()
        
        # 게시글 출력
        print("\n=== Python 서브레딧 최신 게시글 ===\n")
        for i, post in enumerate(posts, 1):
            print(f"{i}. {post.title}")
            print(f"   작성자: {post.author}")
            print(f"   점수: {post.score}")
            print(f"   댓글 수: {post.num_comments}")
            print()
            
    except Exception as e:
        print(f"에러 발생: {str(e)}")

if __name__ == "__main__":
    main()