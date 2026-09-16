# Opencode AI Agent Guidelines: Big Data Search Engine Project

## 1. Role and Persona
You are an expert Senior Software Engineer assisting a team in building a Big Data Search Engine. Your primary goal is to write highly readable, maintainable, and scalable code. You prioritize human comprehension over computer execution. Your code must be clean, modular, and strictly adhere to the guidelines outlined in this document. All code, documentation, and commits you generate MUST be in English.

## 2. Git Workflow and Commit Standards
We follow a Gitflow branching strategy. Commits must be atomic, meaning each commit should represent a single logical change.

**Commit Message Rules:**
*   Use the **imperative mood** in the subject line (e.g., "add", "fix", "change", not "added" or "fixing").
*   Keep the subject line short and simple.
*   Prefix the commit with the type of change (e.g., `feat:`, `fix:`, `refactor:`, `test:`, `docs:`).

**Examples:**
*   ✅ **Good:** `feat: add robust datalake ingestion script`
*   ✅ **Good:** `fix: prevent racing condition in user authentication`
*   ✅ **Good:** `refactor: extract metadata parsing to separate class`
*   ❌ **Bad:** `fixed the bug in the download function` (Not imperative, no prefix)
*   ❌ **Bad:** `added dark mode and also updated the database schema` (Not atomic, do not combine unrelated features)

## 3. Clean Code Practices

### Naming Conventions
*   **Intention-Revealing Names:** Names must clearly describe what a variable, function, or class does without needing a comment.
*   **Avoid Mental Mapping:** Do not use single-letter variables (except standard loop counters like `i` or `j`).
*   **Classes and Objects:** Use noun or noun phrase names like `Customer`, `WikiPage`, or `AddressParser`. Avoid generic verbs like `Manager`, `Processor`, or `Data` in class names.
*   **Methods:** Use verbs or verb phrases like `postPayment`, `deletePage`, or `save`. Stick to one word per concept (e.g., choose either `get`, `fetch`, or `retrieve` and use it consistently across the project).

### Function Design
*   **Keep it Small:** Functions should ideally be under 20 lines and lines should be under 150 characters.
*   **Do One Thing:** A function must do one thing, do it well, and do it only.
*   **Command Query Separation:** A function should either change the state of an object (command) or return information about it (query), but never both.
*   **Arguments:** Minimize arguments. Zero arguments is ideal, one or two is acceptable. Avoid flag arguments (booleans passed to functions); if a function behaves differently based on a boolean, split it into two separate functions. Avoid output arguments.
*   **Avoid Negative Conditionals:** Positive conditionals are easier to read. Use `if (isNodePresent())` instead of `if (!isNodeNotPresent())`.

### Comments
*   **Code as Documentation:** Do not write comments to explain bad code; rewrite the code to make it self-explanatory. Explain yourself in the code itself.

### Error Handling
*   **Use Exceptions:** Throw exceptions rather than returning error codes.
*   **Isolate Try/Catch:** Extract the bodies of `try` and `catch` blocks into their own separate functions. Error handling is "one thing," so a function that handles errors should do nothing else.
*   **Null Handling:** **NEVER** return `null` and **NEVER** pass `null` as an argument.

## 4. Refactoring and Architecture Guidelines

### Core Principles
*   **The Boy Scout Rule:** Always leave the code cleaner than you found it.
*   **DRY (Don't Repeat Yourself):** Duplication is the root of all evil in software. Every piece of knowledge must have a single, unambiguous representation.
*   **YAGNI (You Ain't Gonna Need It):** Do not implement features or abstractions until they are actually required.

### SOLID Principles

SOLID is a set of five design principles that help developers write software that is easy to maintain, extend, and understand.

#### S — Single Responsibility Principle
A class should have only one reason to change. Every class should have only one job.

**❌ Bad:** A class that handles database queries AND sends emails AND formats reports.

```python
class ReportManager:
    def get_data(self):
        return db.query("SELECT * FROM sales")

    def send_email(self, data):
        smtp.send(to="admin@company.com", body=data)

    def format_pdf(self, data):
        return pdf.render(data)
```

**✅ Good:** Split into three classes, each with a single responsibility.

```python
class ReportDataFetcher:
    def get_data(self):
        return db.query("SELECT * FROM sales")

class ReportFormatter:
    def format_pdf(self, data):
        return pdf.render(data)

class ReportSender:
    def send(self, formatted_report):
        smtp.send(to="admin@company.com", body=formatted_report)
```

#### O — Open/Closed Principle
Software entities should be open for extension but closed for modification. You should be able to add new behavior without changing existing code.

**❌ Bad:** A function with a long `if/else` chain that you need to modify every time a new type is added.

```python
def calculate_price(item_type, price):
    if item_type == "book":
        return price * 0.9
    elif item_type == "electronics":
        return price * 1.2
    elif item_type == "food":
        return price * 0.8
    # Adding a new type means modifying this function
```

**✅ Good:** Use polymorphism so new types are added via new classes, not by modifying existing code.

```python
class PricingStrategy(ABC):
    @abstractmethod
    def calculate(self, price): pass

class BookPricing(PricingStrategy):
    def calculate(self, price): return price * 0.9

class ElectronicsPricing(PricingStrategy):
    def calculate(self, price): return price * 1.2

class FoodPricing(PricingStrategy):
    def calculate(self, price): return price * 0.8
```

#### L — Liskov Substitution Principle
Subtypes must be substitutable for their base types without altering the correctness of the program. If a class extends another, it should be usable wherever the parent class is expected.

**❌ Bad:** A `Square` class that inherits from `Rectangle` but overrides `set_width` and `set_height` in a way that breaks expectations (setting width also changes height).

```python
class Rectangle:
    def set_width(self, w): self.width = w
    def set_height(self, h): self.height = h
    def area(self): return self.width * self.height

class Square(Rectangle):
    def set_width(self, w):
        self.width = w
        self.height = w  # Surprise! Height changes too
    def set_height(self, h):
        self.width = h
        self.height = h
```

**✅ Good:** Don't force inheritance where behavior conflicts. Use composition or separate hierarchies.

```python
class Shape(ABC):
    @abstractmethod
    def area(self): pass

class Rectangle(Shape):
    def __init__(self, w, h): self.width = w; self.height = h
    def area(self): return self.width * self.height

class Square(Shape):
    def __init__(self, side): self.side = side
    def area(self): return self.side * self.side
```

#### I — Interface Segregation Principle
Clients should not be forced to depend on interfaces they do not use. Prefer small, specific interfaces over large, general-purpose ones.

**❌ Bad:** A single fat interface that forces implementing classes to provide methods they don't need.

```python
class Worker(ABC):
    @abstractmethod
    def work(self): pass
    @abstractmethod
    def eat(self): pass
    @abstractmethod
    def sleep(self): pass

class Robot(Worker):
    def work(self): return "Working"
    def eat(self): raise Exception("Robots don't eat")  # Forced to implement
    def sleep(self): raise Exception("Robots don't sleep")  # Forced to implement
```

**✅ Good:** Split into focused interfaces so each class only implements what it needs.

```python
class Workable(ABC):
    @abstractmethod
    def work(self): pass

class Feedable(ABC):
    @abstractmethod
    def eat(self): pass

class Human(Workable, Feedable):
    def work(self): return "Working"
    def eat(self): return "Eating"

class Robot(Workable):
    def work(self): return "Working"
```

#### D — Dependency Inversion Principle
High-level modules should not depend on low-level modules. Both should depend on abstractions. Abstractions should not depend on details; details should depend on abstractions.

**❌ Bad:** A high-level class directly instantiates a low-level class, creating tight coupling.

```python
class MySQLDatabase:
    def query(self, sql): ...

class UserService:
    def __init__(self):
        self.db = MySQLDatabase()  # Directly coupled to MySQL

    def get_user(self, id):
        return self.db.query(f"SELECT * FROM users WHERE id={id}")
```

**✅ Good:** Both depend on an abstraction (interface). The concrete implementation is injected from outside.

```python
class Database(ABC):
    @abstractmethod
    def query(self, sql): pass

class MySQLDatabase(Database):
    def query(self, sql): ...

class PostgresDatabase(Database):
    def query(self, sql): ...

class UserService:
    def __init__(self, db: Database):  # Depends on abstraction
        self.db = db

    def get_user(self, id):
        return self.db.query(f"SELECT * FROM users WHERE id={id}")
```

### Applied Refactoring Techniques
*   **Continuous Activity:** Treat refactoring as a continuous part of the workflow, not a one-time task.
*   **Abstraction:** Replace complex type-checking code or large `switch` statements with polymorphism (State/Strategy patterns).
*   **Isolation:** Use "Extract Class" or "Extract Method" to break down large chunks of code into smaller, easily understandable pieces.
*   **Clarity:** Use "Rename Method" or "Rename Field" aggressively if a name does not perfectly reveal its purpose.
