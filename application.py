from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user


application = Flask(__name__)
application.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///ecommerce.db'
application.config["SECRET_KEY"] = "ADLLFND**F34dd"
# Disable event system to avoid overhead warnings
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


login_manager = LoginManager()
db = SQLAlchemy(application)

login_manager.init_app(application)
login_manager.login_view = "login"
CORS(application)


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(60), nullable=False, unique=True)
    password = db.Column(db.String(60), nullable=True)
    cart = db.relationship('CartItem', backref='user', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)


class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    

# Create tables AFTER models are declared so production doesn't 500 on first access
with application.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    # Ensure type compatibility with primary key
    return User.query.get(int(user_id))


@application.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return "Logout realizado."
            

@application.route("/")
def initial():
    return "API up!"


@application.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not data:
        return jsonify({"message": "JSON inválido ou não enviado"}), 400

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"message": "Usuário e senha são obrigatórios"}), 400

    user = User.query.filter_by(username=username).first()

    if user and user.password == password:
        login_user(user)
        return jsonify({"message": "Login realizado com sucesso!"}), 200

    return jsonify({"message": "Acesso não autorizado!"}), 401


@application.route("/api/products/add", methods=["POST"])
@login_required
def add_product():
    try:    
        data = request.json
        product = Product(name=data.get("name", ""), price=data.get("price", ""), description=data.get("description", ""))
        if not product.name:
            return 'Falha ao adicionar produto sem nome!'
        db.session.add(product)
        db.session.commit()
        return 'Produto cadastrado com sucesso!'
    except:
        return 'Falha ao cadastrar produto'        


@application.route("/api/products/delete/<int:product_id>", methods=["DELETE"])
@login_required
def delete_product(product_id):
    product = Product.query.get(product_id)

    if product:
        db.session.delete(product)
        db.session.commit()
        return jsonify({ "message": "Produto deletado com sucesso!" })
    return jsonify({ "message": "Erro ao deletar o produto!" }), 404




@application.route("/api/products/update/<int:product_id>", methods=["PUT"])
@login_required
def update_product_details(product_id):
    product = Product.query.get(product_id)

    if not product:
        return jsonify({ "message": "Erro ao buscar o produto!" }), 404

    data = request.json
    if "name" in data:
        product.name = data["name"]

    if "price" in data:
        product.price = data["price"]

    if "description" in data:
        product.description = data["description"]

    db.session.commit()
    return jsonify({ "message": "Dados atualizados" })

@application.route("/api/products/<int:product_id>", methods=["GET"])
def get_product_details(product_id):
    product = Product.query.get(product_id)

    if product:
        return jsonify({ 
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "description": product.description
        })
    return jsonify({ "message": "Erro ao buscar o produto!" }), 404


@application.route("/api/products", methods=["GET"])
def get_all_product():
    products = Product.query.all()
    product_list = []
    if not products:
        return jsonify({ "message": "Erro ao listar produtos!" }), 404
    
    for product in products:
        product_data = { 
            "id": product.id,
            "name": product.name,
            "price": product.price,
            "description": product.description
        }
        product_list.append(product_data)

    return jsonify(product_list)


@application.route("/api/cart/add/<int:product_id>", methods=['POST'])
@login_required
def add_to_cart(product_id):
    user = User.query.get(int(current_user.id))

    product = Product.query.get(product_id)
    if user and product:
        cart_item = CartItem(user_id=user.id, product_id=product.id)
        db.session.add(cart_item)
        db.session.commit()
        return jsonify({"message": "Produto adicionado ao carrinho."}), 200
    return jsonify({"message": "Falha ao adicionar produto ao carrinho."}), 400

@application.route("/api/cart/remove/<int:product_id>", methods=["DELETE"])
@login_required
def remove_from_cart(product_id):
    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if(cart_item):
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({"message": "Produto removido do carrinho."}), 200
    return jsonify({"message": "Falha ao remover produto do carrinho."}), 400

@application.route('/api/cart/list', methods=['GET']) 
@login_required
def list_from_cart():
    user = User.query.get(int(current_user.id))
    cart_items = user.cart
    cart_list = []

    for cart_item in cart_items:
        product = Product.query.get(cart_item.product_id)
        cart_data = { 
            "id": cart_item.id,
            "user_id": cart_item.user_id,
            "product_id": cart_item.product_id,
            "product_price": product.price
        }
        cart_list.append(cart_data)

    return jsonify(cart_list)


@application.route("/api/cart/checkout", methods=["POST"])
@login_required
def checkout():
    user = User.query.get(current_user.id)
    cart_items = user.cart
    for cart_item in cart_items:
        db.session.delete(cart_item)

    db.session.commit()
    return jsonify({"message": "Compra realizada. Carrinho vazio"})


if __name__ == "__main__":
    application.run(debug=True)