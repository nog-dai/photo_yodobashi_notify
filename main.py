import requests
import sqlite3
import time
import logging
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, date

from environments import CHANNEL_IDS, SLACK_BOT_TOKEN

# グローバル変数
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

# ロガーの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M'  # 年-月-日 時:分
)
logger = logging.getLogger(__name__)


# SQLiteの初期化
def init_db():
    conn = sqlite3.connect('posted_articles.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS articles (id INTEGER PRIMARY KEY, url TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS postings (id INTEGER PRIMARY KEY, article_url TEXT, channel TEXT, UNIQUE(article_url, channel))''')
    conn.commit()
    conn.close()


# フォトヨドバシの新着記事を取得
def fetch_new_articles():
    url = "https://photo.yodobashi.com/"
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        logger.info("Fetched new articles from %s", url)

        articles = []
        for div in soup.find_all("div", class_="new"):
            for link in div.find_all("a", href=True):
                img_tag = link.find("img", alt=True)
                if img_tag:
                    articles.append({
                        "title": img_tag["alt"],
                        "url": url + link["href"],
                    })
        return articles
    except requests.exceptions.RequestException as e:
        print(f"Error fetching articles: {e}")
        return []


# 記事の日付を取得
def get_article_date(article_url):
    try:
        response = requests.get(article_url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        date_tag = soup.find("p", class_="date")
        if date_tag:
            # 日付の余分な部分を削除して解析
            date_text = date_tag.text.strip().strip("()").strip()
            return datetime.strptime(date_text, "%Y.%m.%d").date()
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching article date for {article_url}: {e}")
        return None
    except ValueError as e:
        print(f"Error parsing date for {article_url}: {e}")
        return None


# 新着記事をSlackに投稿
def post_to_slack(article, channels):
    client = WebClient(token=SLACK_BOT_TOKEN)
    for channel in channels:
        if not is_posted_to_channel(article['url'], channel):
            try:
                response = client.chat_postMessage(
                    channel=channel,
                    text=f"記事名: <{article['url']}|{article['title']}>",
                )
                mark_as_posted_to_channel(article['url'], channel)
            except SlackApiError as e:
                print(f"Slack API error in channel {channel}: {e.response['error']}")


# 投稿済みかチェック
def is_posted(article_url):
    conn = sqlite3.connect('posted_articles.db')
    c = conn.cursor()
    c.execute('SELECT id FROM articles WHERE url = ?', (article_url,))
    result = c.fetchone()
    conn.close()
    return result is not None


# チャンネルへの投稿済みかチェック
def is_posted_to_channel(article_url, channel):
    conn = sqlite3.connect('posted_articles.db')
    c = conn.cursor()
    c.execute('SELECT id FROM postings WHERE article_url = ? AND channel = ?', (article_url, channel))
    result = c.fetchone()
    conn.close()
    return result is not None


# 投稿済みとして記録
def mark_as_posted(article_url):
    conn = sqlite3.connect('posted_articles.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO articles (url) VALUES (?)', (article_url,))
    conn.commit()
    conn.close()


# チャンネルへの投稿済みとして記録
def mark_as_posted_to_channel(article_url, channel):
    conn = sqlite3.connect('posted_articles.db')
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO postings (article_url, channel) VALUES (?, ?)', (article_url, channel))
    conn.commit()
    conn.close()


# 新着記事をチェックして投稿
def check_and_post_articles():
    init_db()
    channels = CHANNEL_IDS  # 投稿先チャンネルのリスト
    articles = fetch_new_articles()
    today = date.today() # YYYY-MM-dd の形式

    for article in articles:
        time.sleep(3)
        
        if not is_posted(article['url']):
            article_date = get_article_date(article['url'])
            if article_date == today:
                mark_as_posted(article['url'])
                logger.info(f'本日の未投稿記事なのでSlackへPOST => \n{article}')
                post_to_slack(article, channels)
            else:
                logger.info(f'別日の記事なので静観 => \n{article}')

        else:
            logger.info(f'投稿済み => \n{article}')


if __name__ == "__main__":
    logger.info('------- 実行開始 ------')
    check_and_post_articles()
    logger.info('------- 実行終了 ------')
