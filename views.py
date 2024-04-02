from flask import Flask, request, render_template

app = Flask(__name__)

@app.route('/submit_form', methods=['POST'])
def submit_form():
    name = request.form.get('name')
    last_name = request.form.get('last_name')
    email = request.form.get('email')
    phone = request.form.get('phone')
    question = request.form.get('question')

    # Вывод полученных данных
    print(f'Имя: {name}, Фамилия: {last_name}, Email: {email}, Телефон: {phone}, Вопрос: {question}')

    # После обработки данных можно вернуть сообщение об успехе или перенаправить пользователя
    return 'Форма успешно отправлена!'

@app.route('/')
def index():
    return render_template('test_html.html')

if __name__ == '__main__':
    app.run(debug=True)