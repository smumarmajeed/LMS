class BookNode:
    def __init__(self, book_id, title, author, copies):
        self.book_id = book_id
        self.title = title
        self.author = author
        self.copies = copies
        self.next = None

class BookLinkedList:
    def __init__(self):
        self.head = None

    def add_book(self, book_id, title, author, copies):
        new_node = BookNode(book_id, title, author, copies)
        if not self.head:
            self.head = new_node
        else:
            current = self.head
            while current.next:
                current = current.next
            current.next = new_node

    def update_book(self, book_id, title=None, author=None, copies=None):
        current = self.head
        while current:
            if current.book_id == book_id:
                if title:
                    current.title = title
                if author:
                    current.author = author
                if copies is not None:
                    current.copies = copies
                return True
            current = current.next
        return False

    def delete_book(self, book_id):
        current = self.head
        prev = None
        while current:
            if current.book_id == book_id:
                if prev:
                    prev.next = current.next
                else:
                    self.head = current.next
                return True
            prev = current
            current = current.next
        return False

    def to_list(self):
        books = []
        current = self.head
        while current:
            books.append({
                "id": current.book_id,
                "title": current.title,
                "author": current.author,
                "copies": current.copies
            })
            current = current.next
        return books

    # ✅ FIX: This method must be indented inside the class
    def search_books(self, keyword):
        results = []
        keyword = keyword.lower()
        current = self.head
        while current:
            if keyword in current.title.lower() or keyword in current.author.lower():
                results.append({
                    "id": current.book_id,
                    "title": current.title,
                    "author": current.author,
                    "copies": current.copies
                })
            current = current.next
        return results
class BookQueue:
    def __init__(self):
        self.queue = []

    def enqueue(self, book):
        self.queue.append(book)

    def dequeue(self):
        if self.is_empty():
            return None
        return self.queue.pop(0)

    def is_empty(self):
        return len(self.queue) == 0

    def to_list(self):
        return self.queue
