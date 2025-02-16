"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
from flask import Flask, request, jsonify, url_for, Blueprint, current_app
from api.models import db, User , Evento, eventos, Asistencia, Categoria
from api.utils import generate_sitemap, APIException
from flask_cors import CORS
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required
from datetime import datetime
from flask_mail import Message #importamos Message() de flask_mail
import os




api = Blueprint('app', __name__)
# Allow CORS requests to this API
CORS(api)
BACKEND_URL = os.getenv('BACKEND_URL')

# Setup the Flask-JWT-Extended extension


# POST Para hacer login


@api.route("/login", methods=["POST"])
def login():
    email = request.json.get("email", None)
    password = request.json.get("password", None)
    user_query = User.query.filter_by(email = email).first()
    if user_query is None:
        return jsonify({"msg": "Email doesn't exist."}), 401
    if email != user_query.email or password != user_query.password:
        return jsonify({"msg": "Wrong password or email."}), 401
    access_token = create_access_token(identity=email)
    return jsonify({
        "access_token": access_token,
        "user": {
            "id": user_query.id,
            "email": user_query.email,
            "name": user_query.name
        }
    })


# GET Mostrar todos los eventos proximos
@api.route('/events', methods=['GET'])
def get_users_attend_all_events():
    date = datetime.now()
    all_events = Evento.query.filter(Evento.fecha > date).order_by(Evento.fecha).limit(6).all()
    results_events = list(map(lambda item: item.serialize(), all_events))
    
    response_body = {

        "msg": "Users asisting every events",
        "results": results_events
    }

    return jsonify(response_body), 200


############################ endpoint registro usuario ########### de la linea 50 a la 80#####################

@api.route("/signup", methods=["POST"])
def signup():

    name = request.json.get("name")
    email = request.json.get("email")
    password = request.json.get("password")
    
    ############ manejo de errores ##############
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"msg": "Email is alredy being used."}), 400
    

    new_user = User(name=name, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"msg": "User successfully registered."}), 201




# GET Mostrar detalles Eventos
@api.route('/events/<int:id>', methods=['GET'])
def event(id):
    event_query = Evento.query.filter_by(id = id).first()
    event_data = event_query.serialize()
    num_asistentes = User.query.join(User.eventos).filter(Evento.id == id).count()
    response_body = {
        "msg": "ok",
        "result": event_data,
        "asistentes": num_asistentes
    }

    return jsonify(response_body), 200

# GET User information
@api.route('/user/details', methods=['GET'])
@jwt_required()
def user_detail():
    current_user = get_jwt_identity()
    user_query = User.query.filter_by(email = current_user).first()
    user_data = user_query.serialize()
    eventos = [evento.serialize() for evento in Evento.query.filter_by(user_creador=user_data["id"]).all()]
    user_info ={"id": user_data["id"],
                "name": user_data["name"],
                "email": user_data["email"],
                "hobbies": list(map(lambda item: item["name"], user_data["hobbies"])),
                "num_eventos_asistido": len(user_data["eventos"]),
                "id_eventos": list(map(lambda item: item["id"], user_data["eventos"])),
                "eventos_asistido": list(map(lambda item: item, user_data["eventos"])),
                "num_eventos_creados" : Evento.query.filter_by(user_creador = user_data["id"]).count(),
                "eventos_creados": list(map(lambda item: item, eventos))
                }
    response_body = {
        "msg": "ok",
        "details": user_info
    }
    return jsonify(response_body), 200

##########post para evento #############

@api.route('/event', methods=['POST'])
@jwt_required()
def create_event():
    current_user = get_jwt_identity()
    user_query = User.query.filter_by(email = current_user).first()
    user_data = user_query.serialize()
    id_categoria = request.json["categoria"]
    categoria_query = Categoria.query.filter_by(id=int(id_categoria)).first()
    if not categoria_query:
        return jsonify({"msg": "Category not found"}), 404
    # categoria_data = categoria_query.serialize()
    required_fields = ['evento', 'ciudad', 'ubicacion', 'fecha', 'max_personas']
    if not all(field in request.json for field in required_fields):
        return jsonify({"msg": "Error while creating the event: some fields are required."}), 400
    try:
        new_event = Evento(
            evento=request.json['evento'],
            ciudad=request.json['ciudad'],
            ubicación=request.json['ubicacion'],
            descripcion=request.json['descripcion'],
            fecha=request.json['fecha'],
            precio=request.json['precio'],
            max_personas=request.json['max_personas'],
            id_categoria=categoria_query.id,
            url_img= request.json['url_img'],
            user_creador=user_data["id"]
        )
        db.session.add(new_event)
        db.session.commit()
    except Exception as e:
        return jsonify({"msg": f"Error while creating the event: {str(e)}"}), 500
    return jsonify({"msg": "Event successfully created."}), 201



@api.route('/validate_token', methods=['GET'])
@jwt_required()
def validate_token():
    current_user = get_jwt_identity()
    if(current_user):
        return jsonify({"is_loged": True}), 201
    
    return jsonify({"is_loged": False}), 401

# GET Mostrar detalles Eventos
@api.route('/events/<string:category>', methods=['GET'])

def event_category(category):
    date = datetime.now()
    if category=="ALL":
        event_query = Evento.query.filter(Evento.fecha > date).order_by(Evento.fecha).all()
        event_data = [event.serialize() for event in event_query]
    else: 
        event_query = Evento.query.filter(Evento.categoria.has(categoria=category), Evento.fecha > date).all()
        event_data = list(map(lambda item: item.serialize(), event_query))
        
    response_body = {
        "msg": category,
        "result": event_data,
    }

    return jsonify(response_body), 200



@api.route('/asistir/<int:id>', methods=['POST'])
@jwt_required()
def eventAsist(id):
    current_user = get_jwt_identity()
    user_query = User.query.filter_by(email = current_user).first()
    user_data = user_query.serialize()
    if (user_data["id"]):
        new_asist = Asistencia(user_id= user_data["id"], evento_id= id)
        db.session.add(new_asist)
        db.session.commit()
        return jsonify("Correct event assistance."), 201
    
    return jsonify("User not found."), 400


@api.route('/categories', methods=['GET'])
def get_categories():
    categories = Categoria.query.all()
    categories = [categoria.serialize() for categoria in categories]
    
    response_body = {
        "msg": "ok",
        "results": categories
    }

    return jsonify(response_body), 200


# Eliminar evento endpoint
@api.route('/event/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_event(id):
    current_user = get_jwt_identity()
    user_query = User.query.filter_by(email=current_user).first()
    if not user_query:
        return jsonify({"msg": "User not found."}), 400
    
    event = Evento.query.filter_by(id=id, user_creador=user_query.id).first()
    if not event:
        return jsonify({"msg": "Event not found."}), 400

    db.session.delete(event)
    db.session.commit()
    
    return jsonify({"msg": "Event successfully deleted."}), 200


# Dejar de Asistir a un evento:

@api.route('/asistir/<int:id>', methods=['DELETE'])
@jwt_required()
def dejar_de_asistir(id):
    current_user = get_jwt_identity()
    user_query = User.query.filter_by(email=current_user).first()
    if user_query:
        asistencia = Asistencia.query.filter_by(user_id=user_query.id, evento_id=id).first()
        if asistencia:
            db.session.delete(asistencia)
            db.session.commit()
            return jsonify({"msg": "You left the event. See in the next one!"}), 200
        else:
            return jsonify({"msg": "You are not registered in this event."}), 400
    else:
        return jsonify({"msg": "User not found."}), 404
    
    # Actualizar un evento

@api.route('/event/<int:id>', methods=['PUT'])
@jwt_required()

def update_event(id):
    current_user = get_jwt_identity()
    user_query = User.query.filter_by(email=current_user).first()
    if not user_query:
        return jsonify({"msg": "User not found."}), 400
    
    event = Evento.query.filter_by(id=id, user_creador=user_query.id).first()
    if not event:
        return jsonify({"msg": "Event not found."}), 400

    data = request.json
    if 'evento' in data:
        event.evento = data['evento']
    if 'descripcion' in data:
        event.descripcion = data['descripcion']
    if 'ciudad' in data:
        event.ciudad = data['ciudad']
    if 'ubicacion' in data:
        event.ubicación = data['ubicacion']
    if 'fecha' in data:
        event.fecha = data['fecha']
    if 'precio' in data:
        event.precio = data['precio']
    if 'url_img' in data:
        event.url_img = data['url_img']
    if 'max_personas' in data:
        event.max_personas = data['max_personas']
    
    db.session.commit()
    
    return jsonify({"msg": "Event successfully updated."}), 200

@api.route('/user/<int:id>', methods=['PUT'])
@jwt_required()
def update_user(id):
    current_user = get_jwt_identity()
    user_query = User.query.filter_by(email=current_user).first()

    if not user_query:
        return jsonify({"msg": "User not found."}), 400
    
    if user_query.id != id:
        return jsonify({"msg": "You have no permission for updating this event."}), 400

    data = request.json

    if 'name' in data:
        user_query.name = data['name']
    if 'email' in data:
        user_query.email = data['email']
    if 'password' in data:
        user_query.password = data['password']

    db.session.commit()

    return jsonify({"msg": "User successfully updated."}), 200


#Endpoint email con enlace a recuperación de contraseña
@api.route("/send_pwd_restoration", methods=["POST"])
def send_pwd_restoration():
    print(BACKEND_URL)
    recover_email = request.json['email']
    if not recover_email:
        return jsonify({"msg": "You must enter an email."}), 400
    #busco si el correo existe en mi base de datos
    user = User.query.filter_by(email=recover_email).first()
    if user == None:
        return jsonify({"msg": "Email doesn't exist in our database."}), 400
    # #si existe guardo la nueva contraseña aleatoria
    restoration_token = User.get_reset_token(user)
    db.session.commit()
    #luego se la envio al usuario por correo para que pueda ingresar
    msg = Message("Never Hobby Alone: Restablecimiento de contraseña", recipients=[recover_email])
    msg.html = f"""<p>Hola {user.name},</p>
      <p>Haz click en el siguiente enlace para acceder a la recuperación de contraseña. El enlace estará activo durante 5 minutos:</p>
      <p><strong><a href="https://sample-service-name-xrgb.onrender.com/restore_password/{restoration_token}">https://sample-service-name-xrgb.onrender.com/restore_password/{restoration_token}</a></strong></p>
      <p>El equipo de Never Hobby Alone le desea un buen dia y le agradece su confianza.</p>
      <p>Saludos cordiales.</p>"""
    current_app.mail.send(msg)
    return jsonify({"msg": "En enlace de recuperación ha sido enviado al correo indicado"}), 200



# Endpoint de recuperación de contraseña
@api.route('/restore_password/<string:token>', methods=['POST'])
def restore_password(token):
    user = User.verify_reset_token(token)
    print(user)
    if user == None:
        return jsonify({"msg": "Sorry, the url was already expired. Try to restore your password again."}), 400
    new_password = request.json['new_password']
    user.password = new_password
    db.session.commit()
    return jsonify({"msg": "Password has been successfully updated."}), 200