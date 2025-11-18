"""
Generate test data for person matching
"""

import random
import argparse
from datetime import datetime, timedelta
import pandas as pd
import os
from multiprocessing import Pool, cpu_count
from functools import partial
import jellyfish

# Brazilian names for realistic data - 1000+ first names and last names
FIRST_NAMES = [
    # Original names
    "João", "Maria", "José", "Ana", "Pedro", "Carla", "Paulo", "Juliana",
    "Carlos", "Fernanda", "Ricardo", "Patricia", "Fernando", "Beatriz",
    "Rodrigo", "Camila", "Rafael", "Luciana", "Marcelo", "Adriana",
    # Extended list - Male names
    "Miguel", "Arthur", "Gabriel", "Bernardo", "Davi", "Lucas", "Matheus",
    "Pedro", "Guilherme", "Rafael", "Felipe", "Bruno", "Eduardo", "Thiago",
    "Gustavo", "Diego", "Leonardo", "Henrique", "Vinicius", "Alexandre",
    "André", "Caio", "Daniel", "Fabio", "Giovani", "Hugo", "Igor", "Julio",
    "Leandro", "Murilo", "Nathan", "Otavio", "Renan", "Samuel", "Tiago",
    "Victor", "Wagner", "Xavier", "Yuri", "Vitor", "Renato", "Sergio",
    "Roberto", "Mauricio", "Anderson", "Jefferson", "William", "Jonathan",
    "Nicolas", "Patrick", "Kevin", "Ryan", "Enzo", "Pietro", "Lorenzo",
    "Theo", "Heitor", "Benicio", "Anthony", "Emanuel", "Noah", "Benjamin",
    "Cauã", "Isaac", "Caique", "Breno", "Bryan", "Davi Lucca", "Gael",
    "Joaquim", "Luan", "Martin", "Vicente", "Augusto", "Cesar", "Denis",
    "Elias", "Francisco", "Giovanni", "Helio", "Ivan", "Jonas", "Kaique",
    "Lorenzo", "Marcos", "Nelson", "Orlando", "Pablo", "Quintino", "Ramon",
    "Saulo", "Tales", "Ulisses", "Valentim", "Wesley", "Yago", "Zacarias",
    "Alan", "Alisson", "Brenno", "Cristiano", "Danilo", "Erick", "Fabricio",
    "Gilberto", "Hector", "Iago", "Joao Pedro", "Kaua", "Levi", "Matias",
    "Nicolas", "Oliver", "Pietro", "Rafael", "Sebastian", "Theo", "Vinicius",
    "Wallace", "Xavier", "Yuri", "Joao Miguel", "Joao Gabriel", "Joao Victor",
    "Pedro Henrique", "Guilherme Henrique", "Rafael Henrique", "Lucas Gabriel",
    "Matheus Henrique", "Felipe Augusto", "Bruno Henrique", "Eduardo Henrique",
    "Thiago Henrique", "Gustavo Henrique", "Diego Henrique", "Leonardo Henrique",
    "Henrique Augusto", "Vinicius Augusto", "Alexandre Augusto", "André Luiz",
    "Caio Henrique", "Daniel Augusto", "Fabio Henrique", "Giovani Augusto",
    "Hugo Henrique", "Igor Augusto", "Julio Cesar", "Leandro Augusto",
    "Murilo Henrique", "Nathan Augusto", "Otavio Augusto", "Renan Augusto",
    # Extended list - Female names
    "Alice", "Helena", "Laura", "Valentina", "Heloisa", "Isabella", "Manuela",
    "Julia", "Sophia", "Lorena", "Livia", "Giovanna", "Cecilia", "Eloisa",
    "Lara", "Antonella", "Mariana", "Emanuelly", "Yasmin", "Elisa",
    "Rafaela", "Marina", "Nicole", "Gabriela", "Sara", "Clara", "Leticia",
    "Vitoria", "Bianca", "Larissa", "Amanda", "Isabela", "Melissa", "Eduarda",
    "Aline", "Bruna", "Daniela", "Eliane", "Fabiana", "Gisele", "Heloisa",
    "Ingrid", "Jaqueline", "Karina", "Luana", "Michele", "Natalia", "Olivia",
    "Paola", "Raquel", "Sabrina", "Tatiane", "Vanessa", "Wendy", "Yasmin",
    "Abelha", "Beatrice", "Catarina", "Debora", "Esther", "Flavia", "Gabrielle",
    "Heloisa", "Isadora", "Joana", "Katia", "Lais", "Mirela", "Nadia",
    "Pietra", "Regina", "Simone", "Talita", "Ursula", "Veronica", "Zara",
    "Agatha", "Barbara", "Caroline", "Diana", "Erica", "Fatima", "Gloria",
    "Hilda", "Iris", "Jessica", "Kelly", "Luna", "Monica", "Nina",
    "Priscila", "Rita", "Sofia", "Teresa", "Valeria", "Wanda", "Zelia",
    "Adriele", "Brenda", "Cintia", "Denise", "Elisa", "Fernanda", "Glaucia",
    "Helena", "Iara", "Joyce", "Karla", "Ligia", "Marta", "Norma",
    "Patricia", "Renata", "Sandra", "Tania", "Viviane", "Yara", "Ana Paula",
    "Maria Eduarda", "Ana Carolina", "Maria Clara", "Ana Julia", "Maria Luiza",
    "Ana Beatriz", "Maria Fernanda", "Ana Luiza", "Maria Vitoria", "Ana Clara",
    "Maria Alice", "Ana Sophia", "Maria Helena", "Ana Cecilia", "Maria Valentina",
    "Ana Laura", "Maria Isabela", "Ana Livia", "Maria Laura", "Ana Vitoria",
    "Maria Julia", "Ana Gabriela", "Maria Sophia", "Ana Beatrice", "Maria Cecilia",
    "Ana Valentina", "Maria Antonella", "Ana Isabella", "Maria Giovanna", "Ana Heloisa",
    "Maria Eloisa", "Ana Manuela", "Maria Lara", "Ana Lorena", "Maria Melissa",
    "Ana Marina", "Maria Nicole", "Ana Rafaela", "Maria Sara", "Ana Gabrielle",
    "Maria Leticia", "Ana Bianca", "Maria Larissa", "Ana Amanda", "Maria Eduarda",
    "Luiza", "Melissa", "Nathalia", "Olivia", "Paula", "Raissa", "Stella",
    "Tamires", "Vanessa", "Wanessa", "Yasmin", "Zoe", "Agnes", "Brenda",
    "Clarice", "Dalva", "Elaine", "Fatima", "Gabriela", "Hortencia", "Ivone",
    "Joice", "Karol", "Livia", "Marcia", "Neuza", "Odete", "Poliana",
    "Quiteria", "Rosana", "Silvia", "Terezinha", "Vania", "Zilda", "Adriana",
    "Benedita", "Celia", "Dirce", "Edna", "Francisca", "Graziela", "Hildegard",
    "Iracema", "Janaina", "Karine", "Luciana", "Magali", "Nair", "Olga",
    "Penelope", "Quiteria", "Rosangela", "Sueli", "Tereza", "Vania", "Zuleica",
    "Alice", "Beatriz", "Camila", "Daniela", "Elisa", "Fernanda", "Gabriela",
    "Helena", "Isabela", "Juliana", "Larissa", "Marina", "Natalia", "Patricia",
    "Rafaela", "Sara", "Tatiana", "Valeria", "Yasmin", "Aline", "Bruna",
    "Carolina", "Debora", "Eliane", "Fabiana", "Gisele", "Ingrid", "Jessica",
    "Karina", "Luana", "Mariana", "Nicole", "Olivia", "Priscila", "Raquel",
    "Sabrina", "Tamires", "Vanessa", "Yasmin", "Amanda", "Bianca", "Catarina",
    "Diana", "Erica", "Flavia", "Gloria", "Iara", "Joana", "Kelly",
    "Leticia", "Monica", "Nina", "Paula", "Regina", "Sandra", "Tania",
    "Viviane", "Wanda", "Zelia", "Adriele", "Barbara", "Cintia", "Denise",
    "Eduarda", "Fatima", "Glaucia", "Heloisa", "Isadora", "Joyce", "Karla",
    "Ligia", "Marta", "Norma", "Pietra", "Renata", "Simone", "Talita",
    "Ursula", "Veronica", "Zara", "Agatha", "Brenda", "Caroline", "Clarice",
    "Elaine", "Francisca", "Graziela", "Hilda", "Iris", "Janaina", "Karine",
    "Luna", "Magali", "Nadia", "Olga", "Penelope", "Rita", "Sofia",
    "Teresa", "Vania", "Zilda", "Ana Beatriz", "Ana Carolina", "Ana Clara",
    "Ana Julia", "Ana Laura", "Ana Luiza", "Ana Paula", "Ana Sophia", "Ana Vitoria",
    "Maria Alice", "Maria Cecilia", "Maria Clara", "Maria Eduarda", "Maria Fernanda",
    "Maria Helena", "Maria Isabela", "Maria Julia", "Maria Laura", "Maria Luiza",
    "Maria Sophia", "Maria Valentina", "Maria Vitoria", "Joao Pedro", "Joao Gabriel",
    "Joao Victor", "Pedro Henrique", "Lucas Gabriel", "Matheus Henrique", "Felipe Augusto",
    "Bruno Henrique", "Eduardo Henrique", "Thiago Henrique", "Gustavo Henrique", "Diego Henrique",
    "Leonardo Henrique", "Henrique Augusto", "Vinicius Augusto", "Alexandre Augusto", "André Luiz",
    "Caio Henrique", "Daniel Augusto", "Fabio Henrique", "Giovani Augusto", "Hugo Henrique",
    "Igor Augusto", "Julio Cesar", "Leandro Augusto", "Murilo Henrique", "Nathan Augusto",
    "Otavio Augusto", "Renan Augusto", "Samuel Augusto", "Tiago Augusto", "Victor Augusto",
    "Wagner Augusto", "Xavier Augusto", "Yuri Augusto", "Vitor Augusto", "Renato Augusto",
    "Sergio Augusto", "Roberto Augusto", "Mauricio Augusto", "Anderson Augusto", "Jefferson Augusto",
    "William Augusto", "Jonathan Augusto", "Nicolas Augusto", "Patrick Augusto", "Kevin Augusto",
    "Ryan Augusto", "Enzo Augusto", "Pietro Augusto", "Lorenzo Augusto", "Theo Augusto",
    "Heitor Augusto", "Benicio Augusto", "Anthony Augusto", "Emanuel Augusto", "Noah Augusto",
    "Benjamin Augusto", "Cauã Augusto", "Isaac Augusto", "Caique Augusto", "Breno Augusto",
    "Bryan Augusto", "Gael Augusto", "Joaquim Augusto", "Luan Augusto", "Martin Augusto",
    "Vicente Augusto", "Cesar Augusto", "Denis Augusto", "Elias Augusto", "Francisco Augusto",
    "Giovanni Augusto", "Helio Augusto", "Ivan Augusto", "Jonas Augusto", "Kaique Augusto",
    "Marcos Augusto", "Nelson Augusto", "Orlando Augusto", "Pablo Augusto", "Quintino Augusto",
    "Ramon Augusto", "Saulo Augusto", "Tales Augusto", "Ulisses Augusto", "Valentim Augusto",
    "Wesley Augusto", "Yago Augusto", "Zacarias Augusto", "Alan Augusto", "Alisson Augusto",
    "Brenno Augusto", "Cristiano Augusto", "Danilo Augusto", "Erick Augusto", "Fabricio Augusto",
    "Gilberto Augusto", "Hector Augusto", "Iago Augusto", "Kaua Augusto", "Levi Augusto",
    "Matias Augusto", "Oliver Augusto", "Sebastian Augusto", "Wallace Augusto"
]

LAST_NAMES = [
    # Original names
    "Silva", "Santos", "Oliveira", "Souza", "Rodrigues", "Ferreira", "Alves",
    "Pereira", "Lima", "Gomes", "Costa", "Ribeiro", "Martins", "Carvalho",
    "Rocha", "Almeida", "Nascimento", "Araujo", "Melo", "Barbosa",
    # Extended list
    "Castro", "Dias", "Pinto", "Monteiro", "Moreira", "Cardoso", "Teixeira",
    "Correia", "Vieira", "Mendes", "Nunes", "Moura", "Ramos", "Freitas",
    "Azevedo", "Machado", "Lopes", "Fernandes", "Cavalcanti", "Soares",
    "Barros", "Miranda", "Duarte", "Campos", "Farias", "Xavier", "Medeiros",
    "Cunha", "Nogueira", "Andrade", "Tavares", "Moraes", "Santana", "Reis",
    "Batista", "Matos", "Pires", "Fonseca", "Sampaio", "Braga", "Guimaraes",
    "Coelho", "Franco", "Silveira", "Marques", "Macedo", "Bezerra", "Porto",
    "Viana", "Henriques", "Brito", "Pacheco", "Domingues", "Guerra", "Bueno",
    "Castillo", "Vargas", "Cabral", "Aguiar", "Furtado", "Toledo", "Esteves",
    "Resende", "Bastos", "Motta", "Siqueira", "Coutinho", "Mattos", "Chagas",
    "Lacerda", "Carneiro", "Valle", "Correa", "Brandao", "Cruz", "Evangelista",
    "Sales", "Luz", "Camargo", "Goncalves", "Borges", "Vasconcelos", "Paiva",
    "Pessoa", "Dantas", "Luna", "Peixoto", "Holanda", "Morais", "Chaves",
    "Magalhaes", "Cerqueira", "Mesquita", "Prado", "Reis", "Leite", "Queiroz",
    "Guedes", "Sena", "Lemos", "Leal", "Mendonca", "Castro", "Simoes", "Filho",
    "Junior", "Neto", "Sobrinho", "Segundo", "Terceiro", "Quarto", "Quinto",
    "Abreu", "Alencar", "Amaral", "Amaro", "Amorim", "Antunes", "Assis",
    "Bandeira", "Barreto", "Becker", "Bento", "Bernardes", "Bessa", "Bittencourt",
    "Boaventura", "Botelho", "Brum", "Caldas", "Caldeira", "Camacho", "Camilo",
    "Canuto", "Cardozo", "Carneiro", "Casanova", "Casimiro", "Castello", "Castro",
    "Cavalcante", "Cesar", "Chacon", "Cifuentes", "Cintra", "Cirilo", "Claudio",
    "Clemente", "Coimbra", "Colombo", "Constantino", "Cordeiro", "Corona", "Cortez",
    "Cota", "Crespo", "Crispim", "Cristovao", "Cupertino", "Custodio", "Damasco",
    "Damiao", "David", "Delfino", "Delgado", "Deniz", "Deodoro", "Diniz",
    "Dionisio", "Doria", "Drumond", "Dutra", "Edgar", "Edson", "Elias",
    "Eliseu", "Emiliano", "Enrique", "Ernesto", "Escobar", "Eugenio", "Evangelista",
    "Fabiano", "Fabricio", "Faria", "Fatima", "Fausto", "Feliciano", "Felix",
    "Fernandez", "Ferrari", "Figueira", "Figueiredo", "Firmino", "Flores", "Fonseca",
    "Fontes", "Fortunato", "Fragoso", "Francisco", "Frederico", "Freire", "Frota",
    "Furlan", "Gabriel", "Gadelha", "Galdino", "Gallardo", "Galvao", "Gamboa",
    "Garcia", "Gaspar", "Gentil", "Germano", "Gimenez", "Godinho", "Godoi",
    "Godoy", "Gouveia", "Graca", "Graciano", "Gregorio", "Grimaldi", "Gualberto",
    "Guarani", "Guedes", "Guimaraes", "Gurgel", "Gustavo", "Haas", "Hamilton",
    "Heitor", "Henrique", "Herminio", "Herrera", "Hidalgo", "Hilario", "Honorato",
    "Horacio", "Hugo", "Humberto", "Ibanez", "Iago", "Inacio", "Infante",
    "Inocencio", "Isaac", "Isidoro", "Israel", "Jacome", "Jacinto", "Jardim",
    "Jeronimo", "Joao", "Joaquim", "Jorge", "Jose", "Josue", "Julio",
    "Justino", "Kaiser", "Kalil", "Keller", "Kennedy", "Klaus", "Kruger",
    "Lacerda", "Ladislau", "Lafayette", "Lago", "Lamego", "Lara", "Laureano",
    "Lauro", "Lavinia", "Lazaro", "Leandro", "Lemos", "Leonardo", "Leonel",
    "Liberato", "Lima", "Linhares", "Lino", "Lisboa", "Lobato", "Lobo",
    "Logan", "Loiola", "Longo", "Lopes", "Lorenzo", "Lourenco", "Lucas",
    "Lucena", "Lucio", "Luis", "Luiz", "Lustosa", "Maciel", "Madeira",
    "Magnus", "Maia", "Madureira", "Maldonado", "Malta", "Manoel", "Manuel",
    "Manzano", "Maranhao", "Marcal", "Marcelo", "Marco", "Marcos", "Mariano",
    "Marinho", "Mario", "Martim", "Martinez", "Massaro", "Mateus", "Mauricio",
    "Maximo", "Medina", "Meireles", "Melendez", "Mello", "Meneses", "Mercado",
    "Miguel", "Milano", "Millan", "Miller", "Milton", "Mineiro", "Miranda",
    "Molina", "Moniz", "Monroe", "Monteiro", "Montenegro", "Montes", "Montez",
    "Morales", "Moreira", "Moreno", "Morgan", "Mota", "Mourao", "Mueller",
    "Munhoz", "Muniz", "Murillo", "Nabuco", "Napoleao", "Narciso", "Navarro",
    "Negreiros", "Nelson", "Neves", "Newton", "Nicolau", "Nilo", "Nobrega",
    "Noronha", "Norton", "Novais", "Nunes", "Nuzman", "Obregon", "Octavio",
    "Olegario", "Olinto", "Olimpio", "Oliveira", "Omar", "Orozco", "Ortega",
    "Ortiz", "Oscar", "Osvaldo", "Otero", "Otoni", "Otto", "Ourique",
    "Pacheco", "Padilha", "Paes", "Paiva", "Palacio", "Palma", "Palmer",
    "Parga", "Parreira", "Pascoal", "Pascual", "Passos", "Pastor", "Patricio",
    "Paulo", "Paz", "Pedreira", "Pedro", "Pena", "Penalva", "Penha",
    "Pereira", "Perez", "Pessoa", "Pimentel", "Pinheiro", "Pinto", "Pio",
    "Pires", "Pitanga", "Pizarro", "Platao", "Pondeca", "Ponce", "Pontes",
    "Portela", "Portillo", "Porto", "Portugal", "Portuondo", "Posada", "Povoa",
    "Prado", "Prestes", "Prieto", "Primo", "Proenca", "Prudente", "Puig",
    "Quaresma", "Quental", "Quevedo", "Quijano", "Quintas", "Quintana", "Quirino",
    "Rabelo", "Rafael", "Ramalho", "Ramiro", "Ramon", "Ramos", "Rangel",
    "Raul", "Rebelo", "Recife", "Rego", "Reis", "Renato", "Resende",
    "Reyes", "Ribas", "Ricardo", "Rico", "Rios", "Rivera", "Roberto",
    "Robles", "Rocha", "Rodrigo", "Rodriguez", "Rogerio", "Roldan", "Roman",
    "Romano", "Romao", "Romero", "Ronaldo", "Rosales", "Rosario", "Rossi",
    "Rubens", "Rubio", "Rufino", "Ruiz", "Russo", "Sabino", "Sacramento",
    "Sadler", "Saenz", "Saenz", "Salazar", "Saldanha", "Sales", "Salgueiro",
    "Salinas", "Salles", "Salomao", "Salvador", "Sampaio", "Samuel", "Sanches",
    "Sanchez", "Sandoval", "Santana", "Santiago", "Santillan", "Santo", "Santos",
    "Saraiva", "Sardinha", "Sarmento", "Saul", "Savio", "Schneider", "Sebastiao",
    "Segundo", "Seixas", "Sena", "Sepulveda", "Sequeira", "Serafim", "Sergio",
    "Serra", "Serrano", "Severo", "Severino", "Seyffert", "Silva", "Silvano",
    "Silverio", "Silvestre", "Simao", "Simoes", "Simon", "Simplicio", "Sintra",
    "Soares", "Sobral", "Soeiro", "Solano", "Solis", "Solon", "Somoza",
    "Soria", "Sosa", "Soto", "Sousa", "Souza", "Suarez", "Tadeu",
    "Tafoya", "Tavares", "Taveira", "Teixeira", "Teles", "Tello", "Teodoro",
    "Terence", "Terceiro", "Terra", "Thiago", "Tiago", "Tiburcio", "Timoteo",
    "Tobias", "Toledo", "Tomas", "Torquato", "Torres", "Tovar", "Trajano",
    "Trindade", "Tristan", "Trovao", "Trujillo", "Tulio", "Urbano", "Uribe",
    "Urquiza", "Valdes", "Valencia", "Valentim", "Valente", "Valentin", "Valerio",
    "Valle", "Vallejo", "Valmor", "Valverde", "Varela", "Vargas", "Vasco",
    "Vasconcelos", "Vasques", "Vazquez", "Vega", "Velasco", "Velasquez", "Velho",
    "Venancio", "Venceslau", "Ventura", "Vera", "Verissimo", "Viana", "Vicente",
    "Vidal", "Vieira", "Vigil", "Vila", "Vilela", "Villalobos", "Villar",
    "Villela", "Vinicius", "Vital", "Vitor", "Vitorio", "Viveiros", "Wagner",
    "Wallace", "Walter", "Washington", "Weber", "Wellington", "Wenceslau", "Werner",
    "Wesley", "Wilfred", "William", "Wilson", "Xavier", "Ximenes", "Ynez",
    "Yolanda", "York", "Ytalo", "Yuri", "Yvette", "Zacarias", "Zagalo",
    "Zahar", "Zambrano", "Zanetti", "Zarate", "Zarza", "Zeferino", "Zelia",
    "Zenaide", "Zenobio", "Zeus", "Zilmar", "Zita", "Zoroastro", "Zuber",
    "Zulema", "Zuniga"
]

STATUS_OPTIONS = ["Ativo", "Inativo", "Pendente", "Bloqueado"]


def generate_cpf():
    """Generate a random valid CPF"""
    cpf = [random.randint(0, 9) for _ in range(9)]
    
    # Calculate first digit
    sum1 = sum([(10 - i) * cpf[i] for i in range(9)])
    digit1 = 11 - (sum1 % 11)
    digit1 = 0 if digit1 >= 10 else digit1
    cpf.append(digit1)
    
    # Calculate second digit
    sum2 = sum([(11 - i) * cpf[i] for i in range(10)])
    digit2 = 11 - (sum2 % 11)
    digit2 = 0 if digit2 >= 10 else digit2
    cpf.append(digit2)
    
    return ''.join(map(str, cpf))


def generate_birth_date():
    """Generate a random birth date between 1950 and 2005"""
    start_date = datetime(1950, 1, 1)
    end_date = datetime(2005, 12, 31)
    
    time_between = end_date - start_date
    random_days = random.randrange(time_between.days)
    
    birth_date = start_date + timedelta(days=random_days)
    return birth_date.strftime('%Y-%m-%d')


def generate_person():
    """Generate a random person record"""
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)
    middle_name = random.choice(LAST_NAMES)
    
    return {
        'nome_completo': f"{first_name} {middle_name} {last_name}",
        'data_nascimento': generate_birth_date(),
        'nr_documento': generate_cpf(),
        'status': random.choice(STATUS_OPTIONS)
    }


def introduce_variations(person, variation_rate=0.3):
    """
    Introduce variations to create fuzzy matches
    
    Args:
        person: Original person record
        variation_rate: Probability of introducing a variation
    """
    varied = person.copy()
    
    if random.random() < variation_rate:
        # Name variations
        name_parts = person['nome_completo'].split()
        variation_type = random.choice(['typo', 'abbreviation', 'order'])
        
        if variation_type == 'typo' and len(name_parts[0]) > 3:
            # Introduce typo in first name
            name = list(name_parts[0])
            pos = random.randint(1, len(name) - 2)
            name[pos] = random.choice('abcdefghijklmnopqrstuvwxyz')
            name_parts[0] = ''.join(name)
            varied['nome_completo'] = ' '.join(name_parts)
        
        elif variation_type == 'abbreviation' and len(name_parts) > 2:
            # Abbreviate middle name
            name_parts[1] = name_parts[1][0] + '.'
            varied['nome_completo'] = ' '.join(name_parts)
        
        elif variation_type == 'order' and len(name_parts) > 2:
            # Swap last two names
            name_parts[-1], name_parts[-2] = name_parts[-2], name_parts[-1]
            varied['nome_completo'] = ' '.join(name_parts)
    
    if random.random() < variation_rate * 0.5:
        # Date variations (typos in day/month)
        date_parts = person['data_nascimento'].split('-')
        if random.choice([True, False]):
            # Change day slightly
            day = int(date_parts[2])
            day = max(1, min(28, day + random.choice([-1, 1])))
            date_parts[2] = f"{day:02d}"
        else:
            # Change month slightly
            month = int(date_parts[1])
            month = max(1, min(12, month + random.choice([-1, 1])))
            date_parts[1] = f"{month:02d}"
        varied['data_nascimento'] = '-'.join(date_parts)
    
    return varied


def generate_batch(args):
    """Generate a batch of person records (for parallel processing)"""
    batch_size, seed = args
    random.seed(seed)
    return [generate_person() for _ in range(batch_size)]


def generate_overlap_batch(args):
    """Generate overlapping records with variations (for parallel processing)"""
    batch_size, variation_rate, seed = args
    random.seed(seed)
    batch = []
    for _ in range(batch_size):
        person = generate_person()
        varied = introduce_variations(person, variation_rate)
        batch.append((person, varied))
    return batch


def generate_datasets(num_records, overlap_rate=0.3, variation_rate=0.3):
    """
    Generate two datasets with overlapping records using multiprocessing
    
    Args:
        num_records: Number of records in each dataset
        overlap_rate: Percentage of records that appear in both datasets
        variation_rate: Rate of variations in overlapping records
    """
    num_cores = cpu_count()
    print(f"🚀 Using {num_cores} CPU cores for parallel generation")
    
    dataset1 = []
    dataset2 = []
    
    # Calculate sizes
    unique_to_dataset1 = int(num_records * (1 - overlap_rate))
    unique_to_dataset2 = int(num_records * (1 - overlap_rate))
    overlap_count = num_records - unique_to_dataset1
    
    # Determine batch size for parallel processing
    batch_size = max(1000, num_records // (num_cores * 4))
    
    # Generate unique records for dataset1 in parallel
    print(f"📝 Generating {unique_to_dataset1} unique records for dataset 1...")
    num_batches = (unique_to_dataset1 + batch_size - 1) // batch_size
    batch_args = []
    for i in range(num_batches):
        size = min(batch_size, unique_to_dataset1 - i * batch_size)
        batch_args.append((size, random.randint(0, 1000000) + i))
    
    with Pool(num_cores) as pool:
        batches = pool.map(generate_batch, batch_args)
    
    for batch in batches:
        dataset1.extend(batch)
    
    # Generate unique records for dataset2 in parallel
    print(f"📝 Generating {unique_to_dataset2} unique records for dataset 2...")
    batch_args = []
    for i in range(num_batches):
        size = min(batch_size, unique_to_dataset2 - i * batch_size)
        batch_args.append((size, random.randint(1000000, 2000000) + i))
    
    with Pool(num_cores) as pool:
        batches = pool.map(generate_batch, batch_args)
    
    for batch in batches:
        dataset2.extend(batch)
    
    # Generate overlapping records with variations in parallel
    print(f"🔗 Generating {overlap_count} overlapping records with variations...")
    num_batches_overlap = (overlap_count + batch_size - 1) // batch_size
    overlap_args = []
    for i in range(num_batches_overlap):
        size = min(batch_size, overlap_count - i * batch_size)
        overlap_args.append((size, variation_rate, random.randint(2000000, 3000000) + i))
    
    with Pool(num_cores) as pool:
        overlap_batches = pool.map(generate_overlap_batch, overlap_args)
    
    for batch in overlap_batches:
        for person, varied in batch:
            dataset1.append(person)
            dataset2.append(varied)
    
    # Shuffle datasets
    print("🔀 Shuffling datasets...")
    random.shuffle(dataset1)
    random.shuffle(dataset2)
    
    return dataset1, dataset2


def save_datasets(dataset1, dataset2, output_dir='./data'):
    """Save datasets to parquet files using parallel compression"""
    os.makedirs(output_dir, exist_ok=True)
    
    print("💾 Converting to DataFrames...")
    df1 = pd.DataFrame(dataset1)
    df2 = pd.DataFrame(dataset2)
    
    # Add blocking_key for later use in Spark (but don't partition files)
    print("🔑 Creating blocking keys with Soundex...")
    df1['blocking_key'] = df1.apply(
        lambda row: f"{jellyfish.soundex(row['nome_completo'])}_{row['data_nascimento'][:7]}", 
        axis=1
    )
    df2['blocking_key'] = df2.apply(
        lambda row: f"{jellyfish.soundex(row['nome_completo'])}_{row['data_nascimento'][:7]}", 
        axis=1
    )
    
    print("💾 Saving dataset 1 to parquet...")
    df1.to_parquet(
        f'{output_dir}/dataset1.parquet', 
        index=False,
        engine='pyarrow',
        compression='snappy'
    )
    
    print("💾 Saving dataset 2 to parquet...")
    df2.to_parquet(
        f'{output_dir}/dataset2.parquet', 
        index=False,
        engine='pyarrow',
        compression='snappy'
    )
    
    print(f"✅ Dataset 1: {len(dataset1):,} records saved to {output_dir}/dataset1.parquet")
    print(f"✅ Dataset 2: {len(dataset2):,} records saved to {output_dir}/dataset2.parquet")
    
    # Save sample as CSV for inspection
    print("📄 Saving samples...")
    df1.head(100).to_csv(f'{output_dir}/dataset1_sample.csv', index=False)
    df2.head(100).to_csv(f'{output_dir}/dataset2_sample.csv', index=False)
    
    print(f"📄 Samples saved to {output_dir}/dataset*_sample.csv")


def main():
    import time
    
    parser = argparse.ArgumentParser(description='Generate test data for person matching')
    parser.add_argument('--records', type=int, default=10000, 
                       help='Number of records per dataset')
    parser.add_argument('--overlap', type=float, default=0.3,
                       help='Overlap rate between datasets (0-1)')
    parser.add_argument('--variations', type=float, default=0.3,
                       help='Variation rate for overlapping records (0-1)')
    parser.add_argument('--output', type=str, default='./data',
                       help='Output directory')
    
    args = parser.parse_args()
    
    start_time = time.time()
    
    print(f"🔧 Generating {args.records:,} records per dataset...")
    print(f"📊 Overlap rate: {args.overlap * 100}%")
    print(f"🔀 Variation rate: {args.variations * 100}%")
    
    dataset1, dataset2 = generate_datasets(
        args.records,
        args.overlap,
        args.variations
    )
    
    save_datasets(dataset1, dataset2, args.output)
    
    elapsed = time.time() - start_time
    print(f"\n✨ Done in {elapsed:.2f} seconds!")
    print(f"⚡ Speed: {(args.records * 2 / elapsed):,.0f} records/second")


if __name__ == '__main__':
    main()
