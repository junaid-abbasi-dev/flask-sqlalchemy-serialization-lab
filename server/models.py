from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy.ext.associationproxy import association_proxy
from marshmallow import Schema, fields


metadata = MetaData(naming_convention={
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
})

db = SQLAlchemy(metadata=metadata)


class Customer(db.Model):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)

    # One customer writes many reviews. back_populates links this list
    # to Review.customer so both sides stay in sync.
    reviews = db.relationship('Review', back_populates='customer')

    # Shortcut: customer.items walks reviews and collects each review.item.
    # Without this you would write [review.item for review in customer.reviews].
    items = association_proxy('reviews', 'item')

    def __repr__(self):
        return f'<Customer {self.id}, {self.name}>'


class Item(db.Model):
    __tablename__ = 'items'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    price = db.Column(db.Float)

    # One item can have many reviews. The matching side is Review.item.
    reviews = db.relationship('Review', back_populates='item')

    # Same shortcut in the other direction: item.customers collects
    # review.customer for every review of this item.
    customers = association_proxy('reviews', 'customer')

    def __repr__(self):
        return f'<Item {self.id}, {self.name}, {self.price}>'


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.String)

    # Foreign keys are the actual columns stored in the reviews table.
    # They point at the primary key of the related row.
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'))

    # Relationships are the Python objects those foreign keys point to.
    customer = db.relationship('Customer', back_populates='reviews')
    item = db.relationship('Item', back_populates='reviews')

    def __repr__(self):
        return f'<Review {self.id}, {self.comment}>'


class CustomerSchema(Schema):
    id = fields.Int()
    name = fields.Str()

    # Nested reviews must not include the customer again, or serialization
    # loops forever: customer -> review -> customer -> review...
    # The trailing comma makes ("item", "customer") a tuple. Parentheses
    # alone, like ("customer"), are just a string and Marshmallow rejects them.
    reviews = fields.List(fields.Nested(
        lambda: ReviewSchema(exclude=("item", "customer"))
    ))
    items = fields.List(fields.Nested(
        lambda: ItemSchema(exclude=("reviews", "customers"))
    ))


class ItemSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    price = fields.Float()

    reviews = fields.List(fields.Nested(
        lambda: ReviewSchema(exclude=("item", "customer"))
    ))
    customers = fields.List(fields.Nested(
        lambda: CustomerSchema(exclude=("items", "reviews"))
    ))


class ReviewSchema(Schema):
    id = fields.Int()
    comment = fields.Str()

    # Foreign keys customer_id and item_id are left off on purpose.
    # The nested objects already say which customer and item this is.
    # Nested customer/item drop their own lists so we do not recurse.
    customer = fields.Nested(lambda: CustomerSchema(exclude=("items", "reviews")))
    item = fields.Nested(lambda: ItemSchema(exclude=("reviews", "customers")))
