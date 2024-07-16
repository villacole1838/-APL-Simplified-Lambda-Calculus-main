#Name             |  github
#Leondre Bromfield|  @Leon-dre
#Tichina Buckle   |  @Tichina
#Orville Cole     |  @villas_cole1838
#Nathan Williams  |  @Natjoe


import ply.lex as lex
import ply.yacc as yacc
import google.generativeai as genai
from dotenv import load_dotenv
import os
import logging

load_dotenv()

# Retrieve the API key from environment variables
key = os.getenv('API_KEY')

genai.configure(api_key=key)

# Create the Gemini model
generation_config = {
  "temperature": 0.5,
  "top_p": 0.95,
  "top_k": 64,
  "max_output_tokens": 1024,
  "response_mime_type": "text/plain",
}

model = genai.GenerativeModel(
  model_name="gemini-1.5-flash",
  generation_config=generation_config,
)


# YACC Tokens
tokens = ['LAMBDA', 'DOT', 'LPAREN', 'RPAREN', 'VAR', 'NUMBER']

# regular expressions
t_LAMBDA = r'\#'
t_DOT = r'\.'
t_LPAREN = r'\('
t_RPAREN = r'\)'

t_ignore = ' \t'# Ignores spaces and escape

def t_VAR(t):
    r'[a-z]'
    return t
 
def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t
 
def t_error(t):
    if t.value[0].isupper():
        print(f"[Lex] Illegal character '{t.value[0]}'. Character must be lowercase.")
    else:
        print(f"[Lex] Illegal character '{t.value[0]}' detected.")
    t.lexer.skip(1)

lexer = lex.lex()

# Grammar rules
precedence = (
    ('left', 'DOT'),
    ('left', 'LAMBDA'),
    ('left', 'VAR', 'NUMBER')
)

def p_expr_var(p):
    'expr : VAR'
    p[0] = ('var', p[1])
    
def p_expr_number(p):
    'expr : NUMBER'
    p[0] = ('number', p[1])

def p_expr_func_arg(p):
    'expr : expr expr'
    p[0] = ('func_arg', p[1], p[2])

def p_expr_lambda_expr(p):
    'expr : LAMBDA VAR DOT expr'
    p[0] = ('lambda', p[2], p[4])

def p_expr_parens(p):
    'expr : LPAREN expr RPAREN'
    p[0] = p[2]
    
# Error handling for specific illegal sequences
def p_expr_dot_number_error(p):
    'expr : DOT NUMBER'
    print(f"Syntax error: Unexpected number '{p[2]}' after '.' at position {p.lexpos(2)}.")
    p[0] = None

def p_error(p):
    if p:
        print(f"Syntax error: Unexpected token '{p.value}' at position {p.lexpos}.")
    else:
        print("Syntax error: Unexpected end of input.")

parser = yacc.yacc()

#logging
logging.basicConfig(
    level = logging.DEBUG,
    filename = "parselog.txt",
    filemode = "w+",
    format = "%(filename)10s:%(lineno)4d:%(message)s"
)
log = logging.getLogger()

lex.lex(debug=True,debuglog=log)
yacc.yacc(debug=True,debuglog=log)

# Beta reduction function block start
def replace(var, expr, replacement):
    if expr[0] == 'var':
        if expr[1] == var:
            return replacement
        else:
            return expr
    elif expr[0] == 'number':
        return expr
    elif expr[0] == 'lambda':
        if expr[1] == var:
            return expr
        else:
            return ('lambda', expr[1], replace(var, expr[2], replacement))
    elif expr[0] == 'func_arg':
        return ('func_arg', replace(var, expr[1], replacement), replace(var, expr[2], replacement))
    else:
        return expr

def beta(expr):
    if expr[0] == 'func_arg':
        if expr[1][0] == 'lambda':
            return beta(replace(expr[1][1], expr[1][2], expr[2]))
        else:
            return ('func_arg', beta(expr[1]), beta(expr[2]))
    elif expr[0] == 'lambda':
        return ('lambda', expr[1], beta(expr[2]))
    else:
        return expr

def to_string(expr):
    if expr[0] == 'var':
        return expr[1]
    elif expr[0] == 'number':
        return str(expr[1])
    elif expr[0] == 'lambda':
        return f"#{expr[1]}.{to_string(expr[2])}"
    elif expr[0] == 'func_arg':
        return f"({to_string(expr[1])} {to_string(expr[2])})"
    else:
        return ""

def to_normal_form(expr):
    prev_expr = None
    reduction_steps = 0
    while expr != prev_expr:
        prev_expr = expr
        expr = beta(expr)
        reduction_steps += 1
    return expr, reduction_steps - 1
#Beta reduction function block end

#Error handling code for the parser
def parse_expression(data):
    try:
        ast = parser.parse(data)
        if ast is None:
            raise ValueError("Failed to parse the expression.")
        print("Original AST:", ast)
        return ast
    except ValueError as ve:
        print(f"ValueError: {ve}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

#main function
def blast_off():
    while True:
        try:
            # s is for user input
            s = input("Enter expression (or 'exit' to exit the application): ")
            if s.strip().lower() == 'exit':
               #exit message/easter egg from APL class
                print("Ariane 5 Rocket... colors... oops... I mean Mission Aborted! \n[Language developed by L.Bromfield, T.Buckle, O.Cole, N.Williams]")
                break

            # Tokenize and parse the input
            lexer.input(s)
            for token in lexer:
               #output the tokens
                print(f"Token: {token.type} → {token.value}")

            #calls the parse function to validate the user input/check for errors as well
            ast = parse_expression(s)

            if ast:
                reduced_ast, steps = to_normal_form(ast)
                #checks if it can be reduced
                if steps == 0:
                    print("The expression is already in normal form. Cannot be reduced.")
                    #another check to see if it can be reduced
                elif steps > 0:
                    print("Reduced AST:", reduced_ast)
                    print("Reduced Expression in Normal Form:", to_string(reduced_ast))
                  
                    try:
                        chat_session = model.start_chat(history=[])
                        question = (
                            f"(Imagine that the '#' is a Lambda symbol). "
                            f"Explain how we got to {to_string(reduced_ast)} from {s} "
                            "in terms of BETA reduction from Lambda Calculus."
                        )
                        response = chat_session.send_message(question)
                        print(response.text)
                    except NameError:
                        print("Chat session model is not defined. Skipping chat interaction.")
            else:
                print("Failed to parse the expression. No reduction performed.") #error message if it cannot be parsed.
               
        except EOFError:
            print("Exiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

# Start the interpreter
def intro():
   print("Welcome to the Lambda Calcus Interpreter!- [Developed by L.Bromfield, T.Buckle, O.Cole, N.Williams]")
   blast_off()

intro()