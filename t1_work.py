import json
import glob
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import re
import json
from collections import defaultdict
import os
import random
from datetime import datetime, timedelta

# Функция для чтения данных из JSON файла
def read_json_file(filename):
    with open(filename, 'r', encoding='utf-8') as file:
        return json.load(file)
# Функция для преобразования списка вопросов в новый формат
def transform_questions(questions):
    result = defaultdict(lambda: {"chapter": "", "questions": {}})
    for item in questions:
        chapter_index = item["chapter"].split('.')[0]  # Получаем номер раздела из его названия
        chapter_index = int(chapter_index)  # Преобразуем номер раздела в число
        question_index = len(result[chapter_index]["questions"]) + 1  # Индекс вопроса основан на порядке

        # Заполнение данных раздела, если они еще не были установлены
        if not result[chapter_index]["chapter"]:
            result[chapter_index]["chapter"] = item["chapter"]

        # Добавление вопроса и его ответов в данные раздела
        result[chapter_index]["questions"][question_index] = {
            "question": item["question"],
            "correct_answer": str(item["correct_answer"]),
            "answers": {answer["ind"]: answer["text"] for answer in item["answers"]}
        }

    # Преобразование defaultdict в обычный dict для удобства
    return dict(result)
# Главная функция для обработки файлов и преобразования данных
def read_questions():
    folder_path = ''
    pattern = os.path.join(folder_path, 'questions_*.json')
    all_questions = []

    for file_name in glob.glob(pattern):
        # Чтение и добавление вопросов из каждого файла
        questions = read_json_file(file_name)
        all_questions.extend(questions)

    # Преобразование всех вопросов в новый формат
    questions_data = transform_questions(all_questions)

    return questions_data


# Инициализируем данные вопросов
questions_data = read_questions()


# Функция для чтения токена из файла
def read_token():
    try:
        with open('token.txt', 'r') as file:
            return file.read().strip()  # .strip() удаляет пробельные символы с начала и конца строки
    except FileNotFoundError:
        print('File token.txt not found')
        return None

# Функция для чтения вопросов из всех файлов с паттерном questions_*.json
def read_questions1():
    # chapter
    types = {}
    # Ищем все файлы, соответствующие шаблону
    folder_path = 'questions'
    # folder_path = ''
    pattern = os.path.join(folder_path, 'questions_*.json')
    for file_name in glob.glob(pattern):
        try:
            # with open(file_name, 'r', encoding='utf-8') as file:
            with open(file_name, 'r', encoding='utf-8-sig') as file:
                data = json.load(file)
                for item in data:
                    if item['type'] not in types:
                        types[item['type']] = []
                    types[item['type']].append(item)
        except FileNotFoundError:
            print(f'File {file_name} not found')

    # Отсортировать словарь по числовому значению, извлеченному из ключа
    types = {k: types[k] for k in sorted(types, key=lambda x: int(x.split('. ')[0]))}

    return types



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

    keyboard = []
    keyboard.append([InlineKeyboardButton('Экзамен', callback_data='win1.1')])
    keyboard.append([InlineKeyboardButton('Учить по разделам', callback_data='win1.2')])

    reply_markup = InlineKeyboardMarkup(keyboard)

    context.user_data.clear()

    # Отправляем сообщение или редактируем его в зависимости от контекста
    if update.callback_query:
        # Если функция вызвана из callback-запроса, изменяем существующее сообщение
        await update.callback_query.edit_message_text('Выберите режим:', reply_markup=reply_markup)
    elif update.message:
        # Если функция вызвана командой /start, отправляем новое сообщение
        await update.message.reply_text('Выберите режим:', reply_markup=reply_markup)

# Функция для экранирования специальных символов в MarkdownV2
def escape_markdown(text):
    # В MarkdownV2 следующие символы должны быть экранированы обратным слешем
    escape_chars = '_*[]()~`>#+-=|{}.!'
    # Экранируем специальные символы
    return ''.join(f'\\{char}' if char in escape_chars else char for char in text)

# Функция для обработки выбора типа вопросов и ответов на вопросы
async def handle_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data.split('.')

    # Выбрать режим...
    if data[0] == 'win0':
      await start(update, context)

    # выбран экзамен / раздел
    elif data[0] == 'win1':
        context.user_data.clear()
        # экзамен
        if data[1] == '1':
            context.user_data['exam'] = True
            #Сохраняем время начала и время окончания в словаре
            context.user_data['start_time'] = datetime.now()
            context.user_data['end_time'] = datetime.now() + timedelta(minutes=30)  # Время окончания на 30 минут позже

            # Список для хранения выбранных вопросов
            questions_list = []
            # Итерация по всем разделам
            for chapter, content in questions_data.items():
                # Получаем ключи вопросов и перемешиваем их
                question_keys = list(content['questions'].keys())
                random.shuffle(question_keys)
                # Берем первый вопрос из перемешанного списка
                selected_question = question_keys[0]
                # Добавляем в список в формате "Номер раздела.Номер вопроса"
                questions_list.append(f"{chapter}.{selected_question}")

            context.user_data['questions_list'] = questions_list
            # текущий вопрос
            context.user_data['current_question'] = 0
            # словарь ответов пользователя (правильно не правильно ответил)
            context.user_data['progress'] = {}

            await show_question(update, context)

        # учить по разделам
        elif data[1] == '2':
            keyboard = []
            button = InlineKeyboardButton("Выбрать режим..", callback_data=f'win0')
            keyboard.append([button])
            for chapter_key, chapter_info in questions_data.items():
                chapter_button = InlineKeyboardButton(chapter_info['chapter'], callback_data=f'win2.{chapter_key}')
                keyboard.append([chapter_button])  # Добавляем кнопку раздела в новом ряду
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.callback_query.edit_message_text('Выберите раздел:', reply_markup=reply_markup)

    # Выбрали раздел
    elif data[0] == 'win2':
        context.user_data.clear()

        # выбранный тип раздела (ключ)
        selected_chapter = int(data[1])
        # Получаем список вопросов для заданного раздела
        questions_list = list(questions_data[selected_chapter]['questions'].keys())
        questions_list = [f'{selected_chapter}.{q}' for q in questions_list]
        # Перемешиваем список вопросов в случайном порядке
        random.shuffle(questions_list)
        context.user_data['questions_list'] = questions_list
        # текущий вопрос (индекс)
        context.user_data['current_question'] = 0
        # словарь ответов пользователя (правильно не правильно ответил)
        context.user_data['progress'] = {}

        await show_question(update, context)

    # Нажали на назад/вперед по вопросам
    elif data[0] in ['prev', 'next']:
        # Очищаем информацию о последнем ответе
        context.user_data.pop('last_answer', None)
        context.user_data.pop('show_correct', None)

        # Получаем текущий индекс вопроса
        current_question = context.user_data.get('current_question', 0)
        # получаем список вопросов
        questions_list = context.user_data['questions_list']

        # Проверяем, нужно ли перейти к предыдущему вопросу
        if data[0] == 'prev':
            if current_question > 0:
                context.user_data['current_question'] -= 1
            else:
                context.user_data['current_question'] = len(questions_list) - 1
            await show_question(update, context)
        # Проверяем, нужно ли перейти к следующему вопросу
        elif data[0] == 'next':
            if current_question < len(questions_list) - 1:
                context.user_data['current_question'] += 1
            else:
                context.user_data['current_question'] = 0
            await show_question(update, context)
        # Если не можем перейти (уже на первом или последнем вопросе)
        else:
            if update.callback_query:
                # Здесь вы можете решить, хотите ли вы отправить уведомление пользователю
                await update.callback_query.answer()
    # нажал на вариант ответа
    elif data[0] == 'answer':
        # удалим, что нужно показать правильный ответ, т.к. сначала пользователь может нажать на показать правильный ответ, а потом на кнопку ответа
        context.user_data.pop('show_correct', None)

        # Выбранный ответ (индекс)
        selected_option = int(data[2])
        # Номер нажатой кнопки
        number_answer = int(data[1])

        # текущий вопрос (индекс)
        current_question = context.user_data.get('current_question')
        # получаем номер раздела и вопроса
        questions_list = context.user_data['questions_list']
        question_chapter_number = questions_list[current_question]
        # получим текущий раздел/текущий номер вопроса
        selected_chapter, question_number = map(int, question_chapter_number.split('.'))
        # получаем словарь с вопросом
        question_dic = questions_data[selected_chapter]['questions'][question_number]
        # если не было ответа то запишем правильно ли был дан ответ
        if not question_chapter_number in context.user_data['progress']:
            # 1. номер кнопки которую нажал пользователь 2. правильно ли он ответил
            context.user_data['progress'][question_chapter_number] = [
                # нажатая кнопка/очки за результат
                {number_answer: int(question_dic['correct_answer'] == str(selected_option))},
                # нажатая кнопка/индекс ответа, выбранного пользователем
                str(selected_option)
            ]

        # если нажата новая кнопка
        last_answer = context.user_data.get('last_answer')
        if last_answer != selected_option:
            # запомним кнопку которую нажали
            context.user_data['last_answer'] = selected_option
            context.user_data['number_answer'] = number_answer
            await show_question(update, context)
        else:
            # Если ответ не изменился, просто подтверждаем получение запроса
            if update.callback_query:
                await update.callback_query.answer()
    # показать правильный ответ
    elif data[0] == 'correct':
        # Очищаем информацию о последнем ответе
        context.user_data.pop('last_answer', None)

        # Проверка, был ли уже показан правильный ответ и нужно ли обновлять сообщение
        if 'show_correct' not in context.user_data:
            # текущий вопрос (индекс)
            current_question = context.user_data.get('current_question')
            # получаем номер раздела и вопроса
            questions_list = context.user_data['questions_list']
            question_chapter_number = questions_list[current_question]
            # установим что пользователь не отвечал на вопрос правильно если смотрит подсказку
            if not question_chapter_number in context.user_data['progress']:
                context.user_data['progress'][question_chapter_number] = [
                    {'подсказка': 0},
                    -1
                ]
            # Устанавливаем, что нужно показать правильный ответ
            context.user_data['show_correct'] = True
            await show_question(update, context)
        else:
            # Если правильный ответ уже показан, просто ответим на callback запрос,
            if update.callback_query:
                await update.callback_query.answer()  # Просто подтверждаем получение запроса без сообщений пользователю

    # показать результат экзамена
    elif data[0] == 'exam_result':
        questions_list = context.user_data['questions_list']
        text = ''
        # всего вопрсов
        total_questions = len(questions_list)

        # Добавляем информацию о прогрессе пользователя
        num_correct = 0  # Сумма всех баллов
        # Проходим по каждому элементу в progress
        for key in context.user_data['progress']:
            # Добавляем к сумме значение из первого элемента списка (который является словарём)
            num_correct += list(context.user_data['progress'][key][0].values())[0]


        start_time = context.user_data['start_time']
        # Вычисляем разницу времени
        time_difference = datetime.now() - start_time
        # Преобразуем разницу в секунды
        total_seconds = int(time_difference.total_seconds())
        # Вычисляем минуты и секунды
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        # Форматируем вывод
        time_passed = f"{minutes:02}:{seconds:02}"

        text += f"💡 Вы ответили правильно на *{num_correct} из {total_questions}* за {time_passed}\n\n"


        # Перебираем каждый вопрос в списке
        for n, q_index in enumerate(questions_list,1):
            chapter, question_num = q_index.split('.')  # Разделяем на раздел и номер вопроса
            # словарь вопроса
            questions_dic = questions_data[int(chapter)]['questions'][int(question_num)]


            if q_index in context.user_data['progress']:
                # индекс ответа пользователя на вопрос
                user_answer_ind = context.user_data['progress'][q_index][1]
                # правильно ли ответил пользователь на вопрос
                answer_correct = next(iter(context.user_data['progress'][q_index][0].values()))
                # текст ответа пользователя
                user_answer_text = questions_dic['answers'][int(user_answer_ind)]
            else:
                answer_correct = False
                # текст ответа пользователя
                user_answer_text = "Не отвечали на вопрос"


            # Текст вопрсоа
            question_text = questions_dic['question']
            question_text = escape_markdown(question_text)
            # текст правильного ответа
            correct_answer_text = questions_dic['answers'][int(questions_dic['correct_answer'])]
            correct_answer_text = escape_markdown(correct_answer_text)

            user_answer_text = escape_markdown(user_answer_text)

            text += f'*Вопрос {n}*: {question_text}\n'
            if answer_correct:
                text += f'✅Ответ правильный: {correct_answer_text}\n\n'
            else:
                text += f'❌Ответ неверный\n'
                text += f'*Правильный ответ*: {correct_answer_text}\n'
                text += f'*Ваш ответ*: {user_answer_text}\n\n'

        keyboard = []
        # кнопки перехода к началу
        type_change_button = [
            InlineKeyboardButton("Раздел..", callback_data="win1.2"),
            InlineKeyboardButton("Режим..", callback_data="win0"),
            InlineKeyboardButton("Экзамен..", callback_data="win1.1")
        ]
        keyboard.append(type_change_button)

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем или редактируем сообщение
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='MarkdownV2')

# Функция для отображения текущего вопроса
async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = context.user_data
    # текущий вопрос (индекс)
    current_question = user_data.get('current_question', 0)
    # получаем список раздел.вопрос
    questions_list = user_data['questions_list']
    # всего вопрсов
    total_questions = len(questions_list)
    # текущий вопрос/раздел
    question_chapter_number = questions_list[current_question]

    # получим текущий раздел/текущий номер вопроса
    selected_chapter, question_number = map(int, question_chapter_number.split('.'))

    # получаем словарь вопроса
    question_dic = questions_data[selected_chapter]['questions'][question_number]
    # сам вопрос
    question = question_dic['question']
    # варианты ответов
    answers = question_dic['answers']
    # Правильный ответ
    correct_answer = int(question_dic['correct_answer'])
    # Номер кнопки правильного ответа
    correct_answer_number = correct_answer + 1

    # # получим или сформируем список ответов в случайном порядке
    # if 'answers_list' in context.user_data:
    #     answers_list = context.user_data['answers_list']
    # else:
    #     # Получаем список ответов в виде ключей
    #     answers_list = list(answers.keys())
    #     # Перемешиваем список ответов
    #     random.shuffle(answers_list)
    #     # добавим порядок ответов как мы их перемешали для следующего вызова
    #     context.user_data['answers_list'] = answers_list
    #
    # # Номер кнопки правильного ответа
    # correct_answer_number = answers_list.index(correct_answer)+1

    # Подготавливаем данные вопроса и пользователя
    if question:

        text =''

        # сдаем экзамен
        if 'exam' in context.user_data:
            # Формируем надпись
            end_time = context.user_data['end_time']
            time_format = "%H:%M"  # Формат, показывающий только часы и минуты
            # Выводим, сколько времени осталось
            remaining_time = end_time - datetime.now()
            # Преобразуем оставшееся время в минуты и секунды для более читабельного формата
            remaining_minutes = remaining_time.total_seconds() // 60
            remaining_seconds = remaining_time.total_seconds() % 60
            text += f"🕒 Завершится в *{end_time.strftime(time_format)}*  Осталось: *{int(remaining_minutes):02d}:{int(remaining_seconds):02d}* минут\n\n"


        cleaned_question = re.sub(r"^\d+\.\s*", "", question)
        text += f"📢 *Вопрос \\({current_question + 1} из {total_questions}\\):* {escape_markdown(cleaned_question)}\n"
        if question_chapter_number in user_data['progress']:
            text += f"📌 вы выбрали вариант: *{next(iter(user_data['progress'][question_chapter_number][0]))}*\n"

        # Формируем текст вопроса и варианты ответов
        for n, answer_idx in enumerate(list(answers.keys()),1):
            cleaned_option = re.sub(r"^\d+\.\s*", "", answers[answer_idx])
            text += f"\n\n*Вариант {n}:* {escape_markdown(cleaned_option)}"

        # Обновляем информацию о правильности ответа
        if not 'exam' in context.user_data:
            if 'show_correct' in context.user_data:
                text += f"\n\n⚠️ Правильный ответ: *Вариант {correct_answer_number}*"
            elif 'last_answer' in context.user_data:
                # Номер кнопки которую выбрал пользователь
                number_answer = user_data.get('number_answer', 0)
                if context.user_data['last_answer'] == correct_answer:
                    text += f"\n\n✅ Правильно\!, вы выбрали: *Вариант {number_answer}*"
                else:
                    text += f"\n\n❌ Неверно, ваш ответ: *Вариант {number_answer}*"

            # Добавляем информацию о прогрессе пользователя
            num_correct = 0  # Сумма всех баллов
            # Проходим по каждому элементу в progress
            for key in context.user_data['progress']:
                # Добавляем к сумме значение из первого элемента списка (который является словарём)
                num_correct += list(context.user_data['progress'][key][0].values())[0]

            text += f"\n\n💡 Вы ответили правильно на {num_correct} из {total_questions}"


        # кнопки ответов
        keyboard = [
            [
                InlineKeyboardButton(str(n), callback_data=f"answer.{n}.{answer_idx}") for n, answer_idx in enumerate(list(answers.keys()), 1)
            ]
        ]
        # кнопки навигации по вопросам
        navigation_buttons = []
        navigation_buttons.append(InlineKeyboardButton("<<", callback_data="prev"))
        if not 'exam' in context.user_data:
            navigation_buttons.append(InlineKeyboardButton("Ответ", callback_data="correct"))
        navigation_buttons.append(InlineKeyboardButton(">>", callback_data="next"))
        keyboard.append(navigation_buttons)

        # результат экзамена
        if 'exam' in context.user_data:
            exam_button = [
                InlineKeyboardButton("Результат экзамена", callback_data="exam_result"),
            ]
            keyboard.append(exam_button)

        # кнопки перехода к началу
        type_change_button = [
            InlineKeyboardButton("Раздел..", callback_data="win1.2"),
            InlineKeyboardButton("Режим..", callback_data="win0")
        ]
        keyboard.append(type_change_button)

        reply_markup = InlineKeyboardMarkup(keyboard)

        # Отправляем или редактируем сообщение
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='MarkdownV2')


# Добавляем обработчики и запускаем бота
def main() -> None:
    token = read_token()

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(handle_selection))
    application.run_polling()


if __name__ == '__main__':
    main()


