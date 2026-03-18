import csv
from sqlalchemy import Column, Integer, Date, String, Float,\
      Boolean, Date, create_engine, ForeignKey, func, extract, distinct
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, joinedload
from sqlalchemy.ext.associationproxy import association_proxy
from datetime import date
from flask import Flask, jsonify, abort, request
import calendar
from data import Book, Author, Student, Receiving_book

app = Flask(__name__)

engine = create_engine('sqlite:///library.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()


@app.route("/author_books", methods=["GET"])
def find_author_books():
    """Поиск книг автора"""
    author_id = request.args.get("author_id", type=int)
    if author_id is None:
        abort(400, description="Укажите author_id в query-параметрах (например: ?author_id=1)")

    result = session.query(Book).options(
        joinedload(Book.author))\
        .filter(
        Book.author_id == author_id,
        Book.count != 0
        ).all()

    if result:
        books_list = []
        for i_book in result:
            book_as_dict = i_book.to_json()
            books_list.append(book_as_dict)
        return jsonify(matched_books=books_list), 200
    return jsonify({"error":
                     f"There is no book by author with id {author_id}"}), 400
    
@app.route("/other_books_by_author", methods=["GET"])
def other_books_by_author():
    """Находим книги которые были написаны автором, книги которого студент уже читал"""
    student_id = request.args.get("student_id", type=int)
    if student_id is None:
        abort(400, description="Укажите student_id в query-параметрах")

    author_ids_subq = (
        session.query(Author.id)
        .join(Author.books)
        .join(Receiving_book, Receiving_book.book_id == Book.id)
        .filter(Receiving_book.student_id == student_id)
        .distinct()
        .subquery()
    )

    # author_ids_subq = (
    #     session.query(distinct(Author.id))\
    #     .join(Author.books)\
    #     .join(Book.receiving_books)\
    #     .filter(Receiving_book.student_id == student_id)\
    #     .subquery()
    #     )

    # выводим все книги этого автора
    books = (
        session.query(Book)
        .options(joinedload(Book.author))
        .outerjoin(
            Receiving_book,
            (Receiving_book.book_id == Book.id)
            & (Receiving_book.student_id == student_id),
        )
        .filter(
            Book.author_id.in_(author_ids_subq),
            Book.count != 0,
            # проверяем, что книги еще не было в receiving_bookы
            Receiving_book.id.is_(None),
        )
        .all()
    )
    if not books:
        return jsonify({"message": 
                         "Для этого студента нет непрочитанных книг тех авторов, которых он уже читал."}),200
    
    books_list = []
    for book in books:
        data = book.to_json()
        if book.author:
            data["author"] = f"{book.author.name} {book.author.surname}"
        books_list.append(data)

    return jsonify(books=books_list, total=len(books_list)), 200

@app.route("/avarage_book_in_month", methods=["GET"])
def avarage_books_in_month():
    """Поулчить сколько книг читают студенты сейчас"""
    today = date.today()

    start_of_month = date(today.year, today.month, 1)
    days_passed = today.day
    days_in_month = calendar.monthrange(today.year, today.month)[1]

    # ищем кол-во книг, забранных в этом месяце
    books_taken = (
        session.query(Receiving_book)
        .filter(
            Receiving_book.date_of_issue >= start_of_month,
            Receiving_book.date_of_issue <= today
        )
        .count()
    )

    # прогноз среднего кол-ва книг взятых за месяц
    average_per_month = (
        books_taken / days_passed * days_in_month
        if days_passed else 0
    )

    return jsonify({
        "books_taken_so_far": books_taken,
        "days_passed": days_passed,
        "days_in_month": days_in_month,
        "average_books_per_month": round(average_per_month, 2)
    }), 200

@app.route("/most_popular_book", methods=["GET"])
def get_most_popular_book():
    """Вывести самую популярную книгу у студентов, у которых средний балл выше 4.0"""
    mininal_avg_score = 4.0

    # поулчаем список студентов, у которых средний балл выше 4.0
    popular_book = session.query(Book.name,
         func.count(Receiving_book.id).label("times_taken"))\
        .join(Receiving_book.book)\
        .join(Student, Student.id==Receiving_book.student_id)\
        .filter(Student.average_score>mininal_avg_score)\
        .group_by(Book.name).order_by(func.count(Receiving_book.id).desc())\
        .limit(1)

    # если нужно вывести топ книг, то выше вместо limit(1) написать all()
    result = [
        {"book": name, "times_taken": count}
            for name, count in popular_book]

    return jsonify(result), 200

@app.route("/most_frequently_reading_students", methods=["GET"])
def get_top_readers():
    """Выводим самых читающих студентов этого года"""
    cur_year = date.today().year

    top_readers = session.query(Student.name, Student.surname,
                    func.count(Receiving_book.id).label("times_took_book"))\
                    .join(Receiving_book, Receiving_book.student_id==Student.id)\
                    .filter(extract("year", Receiving_book.date_of_issue)==cur_year)\
                    .group_by(Student.id).order_by(func.count(Receiving_book.id).desc())\
                    .all()
    
    result = [
        {"name": name, "surname": surname, "count": count}
         for name, surname, count in top_readers
    ]

    return jsonify(result), 200


@app.route("/students/import-csv", methods=["POST"])
def import_students_csv():
    """Импорт студентов из CSV-файла (разделитель ;)"""
    file = request.files.get("file")

    if not file:
        return jsonify({"error": "File is not received"}), 400

    if not file.filename.endswith(".csv"):
        return jsonify({"error": "File forms is not .csv"}), 400

    try:
        decoded_file = file.stream.read().decode("utf-8").splitlines()
        reader = csv.DictReader(decoded_file, delimiter=";")

        students_data = []

        for row in reader:
            students_data.append({
                "name": row["name"],
                "surname": row["surname"],
                "phone": row["phone"],
                "email": row["email"],
                "average_score": float(row["average_score"]),
                "scholarship": row["scholarship"].lower() in ("true", "1", "yes", "false", "0", "no")
            })

        if not students_data:
            return jsonify({"error": "CSV is empty"}), 400

        session.bulk_insert_mappings(Student, students_data)
        session.commit()

        return jsonify({
            "message": "Students are imported",
            "inserted": len(students_data)
        })

    except KeyError as e:
        session.rollback()
        return jsonify({"error": f"There is no column: {str(e)}"}), 400

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    

if __name__ == "__main__":
    app.run()
