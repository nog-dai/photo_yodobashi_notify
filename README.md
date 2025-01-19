# フォトヨドバシ新着記事のSlack通知機能

## 概要

- フォトヨドバシはRSSフィード未対応なので、新着記事を拾うのがほぼ手動となる
- 自動で拾ってSlackに通知したいので本機能を作成した

## 前提

- 作者はラズパイのcronで本Pythonプログラムを定期実行させている
- crontabの例

```sh
*/10 * * * * /usr/bin/sh /root/git/photo_yodobashi_notify/photo_yodobashi_notify.sh
```

- photo_yodobashi_notify.sh の例

```sh
#!/bin/bash

PATH=/root/.pyenv/plugins/pyenv-virtualenv/shims:/root/.pyenv/shims:/root/.pyenv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.pyenv/shims/pip3
/root/.pyenv/shims/python3 /root/git/photo_yodobashi_notify/main.py > /root/git/photo_yodobashi_notify/output.log 2>&1
```
