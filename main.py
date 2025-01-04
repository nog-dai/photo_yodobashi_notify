import requests
import sqlite3
from bs4 import BeautifulSoup
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

from environments import CHANNEL_IDS
from secret_token import SLACK_BOT_TOKEN


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
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)  # タイムアウトを15秒に設定
        response.raise_for_status()  # HTTPエラーを検出
        soup = BeautifulSoup(response.content, "html.parser")

        articles = []
        for div in soup.find_all("div", class_="new"):
            for link in div.find_all("a", href=True):
                img_tag = link.find("img", alt=True)
                if img_tag:
                    articles.append({
                        "title": img_tag["alt"],
                        "url": url + link["href"],
                    })

        print(articles)
        return articles
    except requests.exceptions.RequestException as e:
        print(f"Error fetching articles: {e}")
        return []

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
    for article in articles:
        if not is_posted(article['url']):
            mark_as_posted(article['url'])
        post_to_slack(article, channels)

if __name__ == "__main__":
    check_and_post_articles()
