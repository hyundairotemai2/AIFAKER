from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# 임시 데이터 저장
posts = []
comments = {}

@app.route('/')
def index():
    return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = posts[post_id]
    post_comments = comments.get(post_id, [])
    return render_template('post_detail.html', post=post, post_id=post_id, comments=post_comments)

@app.route('/new', methods=['GET', 'POST'])
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        post_id = len(posts)
        posts.append({'title': title, 'content': content})
        return redirect(url_for('index'))
    return render_template('new_post.html')

@app.route('/post/<int:post_id>/comment', methods=['POST'])
def add_comment(post_id):
    comment = request.form['comment']
    if post_id not in comments:
        comments[post_id] = []
    comments[post_id].append(comment)
    return redirect(url_for('post_detail', post_id=post_id))

if __name__ == '__main__':
    # app.run(port=5011, debug=True)  # 개발 환경에서 사용
    pass