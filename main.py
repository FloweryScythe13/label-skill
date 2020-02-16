from flask import Flask, redirect, url_for, request, make_response, current_app, jsonify
import json
import plac
from spacy.lang.en import English
from spacy.matcher import PhraseMatcher
from spacy.tokens import Doc, Span, Token
import spacy
import pandas as pd
import traceback
import os
import logging

logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter(
        '%(asctime)s %(name)-12s %(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)



def compose_response(json_data):
    values = json.loads(json_data)['values']
    
    # Prepare the Output before the loop
    results = {}
    results["values"] = []
    
    for value in values:
        output_record = transform_value(value)
        if output_record != None:
            results["values"].append(output_record)
    return results

## Perform an operation on a record
def transform_value(value):
    try:
        recordId = value['recordId']
    except AssertionError  as error:
        return None

    # Validate the inputs
    try:         
        assert ('data' in value), "'data' field is required."
        data = value['data']        
        assert ('doc' in data), "'doc' field is required in 'data' object."
        
    except AssertionError  as error:
        return (
            {
            "recordId": recordId,
            "errors": [ { "message": "Error:" + error.args[0] }   ]       
            })

    try:                
        #concatenated_string = value['data']['text1'] + " " + value['data']['text2']  
        # Here you could do something more interesting with the inputs
        annotated_doc = annotate_doc(value['data']['doc'])
    except Exception as e:
        print(e)
        print(traceback.format_exc())
        logger.debug(traceback.format_exc())
        return (
            {
            "recordId": recordId,
            "errors": [ { "message": "Could not complete operation for record. >"  + traceback.format_exc() }   ]       
            })

    return ({
            "recordId": recordId,
            "data": {
                "result": annotated_doc
                    }
            })

def annotate_doc(raw_doc):
    nlp = spacy.load("en_core_web_sm")
    nlp.add_pipe(nlp.create_pipe('sentencizer'), first=True)
    custom_tags = CustomTagsComponent(nlp)  # initialise component
    nlp.add_pipe(custom_tags)  # add it to the pipeline
    nlp.remove_pipe("ner")
    print("Pipeline", nlp.pipe_names)
    doc = nlp(raw_doc)
    param = [[token.text, token.tag_] for token in doc]
    df=pd.DataFrame(param)
    headers = ['text',  'tag']
    df.columns = headers  

    output = []
    for sent in doc.sents:
        line = { "sentence" : sent.text}
        line["annotations"] = []
        for token in sent:
            line["annotations"].append({"token": token.text, "POS": token.tag_, "label": 'O' if token._.type == False else token._.type})
        output.append(line)
    
    return output

class CustomTagsComponent(object):
   

    name = "custom_tags"  # component name, will show up in the pipeline

    def __init__(self, nlp, label="GPE"):
        """Initialise the pipeline component. The shared nlp instance is used
        to initialise the matcher with the shared vocab, get the label ID and
        generate Doc objects as phrase match patterns.
        """
        # Make request once on initialisation and store the data
        labels = []
        APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        
        with open(os.path.join(APP_ROOT, 'labels.json')) as f:
        #with current_app.open_resource("labels.json") as f:
            labels = json.loads(f.read())
        
        self.labels = { c["name"]: c for c in labels}
        self.label = nlp.vocab.strings[label]  # get entity label ID

        # Set up the PhraseMatcher with Doc patterns for each country name
        patterns = [nlp(c) for c in self.labels.keys()]
        self.matcher = PhraseMatcher(nlp.vocab)
        self.matcher.add("PRODUCTS", None, *patterns)

        # Register attribute on the Token. We'll be overwriting this based on
        # the matches, so we're only setting a default value, not a getter.
        # If no default value is set, it defaults to None.
        Token.set_extension("is_product", default=False, force=True)
        Token.set_extension("type", default=False, force=True)


        # Register attributes on Doc and Span via a getter that checks if one of
        # the contained tokens is set to is_country == True.
        Doc.set_extension("has_product", getter=self.has_product, force=True)
        Span.set_extension("has_product", getter=self.has_product, force=True)

    def __call__(self, doc):
        """Apply the pipeline component on a Doc object and modify it if matches
        are found. Return the Doc, so it can be processed by the next component
        in the pipeline, if available.
        """
        matches = self.matcher(doc)
        spans = []  # keep the spans for later so we can merge them afterwards
        for _, start, end in matches:
            # Generate Span representing the entity & set label
            entity = Span(doc, start, end, label=self.label)
            spans.append(entity)
            # Set custom attribute on each token of the entity
            # Can be extended with other data returned by the API, like
            # currencies, country code, flag, calling code etc.
            first = True
            for token in entity:
                token._.set("is_product", True)
                if(first):
                    token._.set("type", "B-" + self.labels[entity.text]["type"])
                else:
                    token._.set("type", "I-" + self.labels[entity.text]["type"])
                first = False

            # Overwrite doc.ents and add entity  be careful not to replace!
            doc.ents = list(doc.ents) + [entity]
        
        return doc  # don't forget to return the Doc!

    def has_product(self, tokens):
        """Getter for Doc and Span attributes. Returns True if one of the tokens
        is a country. Since the getter is only called when we access the
        attribute, we can refer to the Token's 'is_country' attribute here,
        which is already set in the processing step."""
        return any([t._.get("is_product") for t in tokens])

def save_labels(body):
    with open('labels.json', 'r+', encoding='utf-8') as f:
        
        f.seek(0)
        json.dump(body, f, ensure_ascii=False, indent=4)
        f.truncate()


def create_app():
    app = Flask(__name__)
    app.logger.setLevel(logging.DEBUG)

    @app.route("/", methods = ['GET'])
    def index_get():
        content = "To invoke the skill POST the custom skill request payload to the /label endpoint. To set the custom entities, POST to the /annotations endopoint. For a sample, GET the /annotations."
        return make_response(content, 200)

    @app.route("/annotations", methods = ['GET'])
    def annotations_get():
        APP_ROOT = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(APP_ROOT, 'labels.json')) as f:
    
            labels = json.loads(f.read())
            return jsonify(labels)
        return make_response("Error reading labels.json", 500)
            
                
    @app.route("/annotations", methods = ['POST'])
    def annotations():
        try:
            body = request.get_json()
        except ValueError:
            resp = make_response("Invalid body", 400)
            return resp
    
        if body:
            result = save_labels(body)
            return jsonify(result), 201
        else:
            resp = make_response("Invalid body", 400)
            return resp


    @app.route("/label", methods = ['POST'])
    def index():
        try:
            body = json.dumps(request.get_json())
        except ValueError:
            resp = make_response("Invalid body", 400)
            return resp
    
        if body:
            result = compose_response(body)
            return jsonify(result)
        else:
            resp = make_response("Invalid body", 400)
            return resp

    return app

if __name__ == '__main__':
    app = create_app()
    app.run()    