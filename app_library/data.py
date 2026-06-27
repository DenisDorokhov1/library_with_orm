from sqlalchemy import (
    Column,
    Integer,
    Date,
    String,
    Float,
    Boolean,
    create_engine,
    ForeignKey,
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, joinedload
from sqlalchemy.ext.associationproxy import association_proxy
from datetime import date

engine = create_engine("sqlite:///library.db")
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()


class Author(Base):
    __tablename__ = "authors"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)

    books = relationship("Book", back_populates="author")

    def __repr__(self):
        return f"{self.name}, {self.surname}"


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    count = Column(Integer, default=1)
    release_date = Column(Date, nullable=False)
    author_id = Column(ForeignKey("authors.id", ondelete="CASCADE"), nullable=False)

    author = relationship("Author", back_populates="books")
    students = association_proxy(
        "receiving_books",
        "student",
        creator=lambda student: Receiving_book(
            student=student, date_of_issue=date.today()
        ),
    )

    def __repr__(self):
        return f"{self.name}, {self.release_date}, {self.author_id}"

    def to_json(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    surname = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String, nullable=False)
    average_score = Column(Float, nullable=False)
    scholarship = Column(Boolean, nullable=False)

    books = association_proxy("receiving_books", "book")

    def __repr__(self):
        return f"""{self.name}, {self.surname}, {self.phone},
       {self.email}, {self.average_score}, {self.scholarship}"""


class Receiving_book(Base):
    __tablename__ = "receiving_books"

    id = Column(Integer, primary_key=True)
    book_id = Column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    date_of_issue = Column(Date, nullable=False)
    date_of_return = Column(Date)

    student = relationship(
        "Student", backref="receiving_books", lazy="selectin", passive_deletes=True
    )
    book = relationship(
        "Book", backref="receiving_books", lazy="selectin", passive_deletes=True
    )

    def __repr__(self):
        return f"""{self.book_id}, {self.student_id}
       {self.date_of_issue}, {self.date_of_return}"""


def insert_data():
    authors = [
        Author(name="Александр", surname="Пушкин"),
        Author(name="Лев", surname="Толстой"),
        Author(name="Михаил", surname="Булгаков"),
    ]
    authors[0].books.extend(
        [
            Book(name="Капитанская дочка", count=5, release_date=date(1836, 1, 1)),
            Book(name="Евгений Онегин", count=3, release_date=date(1838, 1, 1)),
        ]
    )
    authors[1].books.extend(
        [
            Book(name="Война и мир", count=10, release_date=date(1867, 1, 1)),
            Book(name="Анна Каренина", count=7, release_date=date(1877, 1, 1)),
        ]
    )
    authors[2].books.extend(
        [
            Book(name="Морфий", count=5, release_date=date(1926, 1, 1)),
            Book(name="Собачье сердце", count=3, release_date=date(1925, 1, 1)),
        ]
    )

    students = [
        Student(
            name="Nikita",
            surname="Ivanov",
            phone="2",
            email="3",
            average_score=4.5,
            scholarship=True,
        ),
        Student(
            name="Vlad",
            surname="Petrov",
            phone="2",
            email="3",
            average_score=3.5,
            scholarship=False,
        ),
        Student(
            name="Denis",
            surname="D",
            phone="3",
            email="5",
            average_score=4.1,
            scholarship=True,
        ),
        Student(
            name="Olga",
            surname="Davis",
            phone="6",
            email="7",
            average_score=4.5,
            scholarship=False,
        ),
    ]
    session.add_all(authors)
    session.add_all(students)
    session.commit()


def give_me_book():
    nikita = session.query(Student).filter(Student.name == "Nikita").one()
    vlad = session.query(Student).filter(Student.name == "Vlad").one()
    denis = session.query(Student).filter(Student.name == "Denis").one()
    olga = session.query(Student).filter(Student.name == "Olga").one()
    books_to_nik = (
        session.query(Book).join(Author).filter(Author.surname == "Толстой").all()
    )
    books_to_vlad = session.query(Book).filter(Book.id.in_([1, 3, 4])).all()
    books_to_denis = session.query(Book).filter(Book.id.in_([1, 3, 4])).all()
    books_to_olga = session.query(Book).filter(Book.id.in_([4, 5, 6])).all()

    print(books_to_nik)
    print(books_to_vlad)
    for book in books_to_nik:
        if book.count <= 0:
            print(
                f"Предупреждение: книгу «{book.name}» (id={book.id}) брать нельзя — в наличии 0 экземпляров."
            )
            continue
        receiving_book = Receiving_book()
        receiving_book.book_id = book.id
        receiving_book.student_id = nikita.id
        receiving_book.date_of_issue = date.today()
        session.add(receiving_book)
        book.count -= 1

    for book in books_to_vlad:
        if book.count <= 0:
            print(
                f"Предупреждение: книгу «{book.name}» (id={book.id}) брать нельзя — в наличии 0 экземпляров."
            )
            continue
        receiving_book = Receiving_book()
        receiving_book.book_id = book.id
        receiving_book.student_id = vlad.id
        receiving_book.date_of_issue = date(2022, 3, 5)
        session.add(receiving_book)
        book.count -= 1

    for book in books_to_denis:
        if book.count <= 0:
            print(
                f"Предупреждение: книгу «{book.name}» (id={book.id}) брать нельзя — в наличии 0 экземпляров."
            )
            continue
        receiving_book = Receiving_book()
        receiving_book.book_id = book.id
        receiving_book.student_id = denis.id
        receiving_book.date_of_issue = date(2025, 11, 5)
        session.add(receiving_book)
        book.count -= 1

    for book in books_to_olga:
        if book.count <= 0:
            print(
                f"Предупреждение: книгу «{book.name}» (id={book.id}) брать нельзя — в наличии 0 экземпляров."
            )
            continue
        receiving_book = Receiving_book()
        receiving_book.book_id = book.id
        receiving_book.student_id = olga.id
        receiving_book.date_of_issue = date.today()
        session.add(receiving_book)
        book.count -= 1

    session.commit()


if __name__ == "__main__":
    Base.metadata.create_all(engine)
    check_exist = session.query(Author).all()
    if not check_exist:
        insert_data()
        give_me_book()

    session.commit()
