from flask import Flask
from flask_restful import reqparse, abort, Api, Resource
import requests
import json
import spacy
import time
from datetime import datetime, timedelta

app = Flask(__name__)
api = Api(app)


parser = reqparse.RequestParser()
parser.add_argument('content')
parser.add_argument('doc1')
parser.add_argument('doc2')
parser.add_argument('mot')



nlp = spacy.load("en_core_web_lg")

 

f = open('data.json')
data = json.load(f)


file = open('types.json')
 


typ = json.load(file)

def takeDate(elem):
    return elem['dateTime']

data.sort(key=takeDate)






def getNER(text):
    offsets = []
    res = []
    headers = {
        'accept': 'application/json',
    }
    params = (
        ('text', text),
    )
    response = requests.get(
        'https://api.dbpedia-spotlight.org/en/candidates', headers=headers, params=params)
    try:
        responses = response.json()
        for line in responses['annotation']['surfaceForm']:
            tup = (line['@name'], line['resource']['@uri'])
            offset = (line['@name'], int(line['@offset']))
            # if tup not in res:
            res.append(tup)
            offsets.append(offset)
    except ValueError:
        pass
    except TypeError:
        pass
    except KeyError:
        pass
    return [res, offsets]


def getTypes(text):
    for ar in typ:
        if ar==text:
            return typ[ar]
    return None


def orderByTopType(data):
    person = {}
    organization = {}
    event = {}
    artifact = {}
    yagogeoentity = {}
    for word in data:
        for type in data[word]:
            if "person" in type:
                person[word] = data[word]
            else:
                if "organization" in type:
                    organization[word] = data[word]
                else:
                    if 'event' in type:
                        event[word] = data[word]
                    else:
                        if 'artifact' in type:
                            artifact[word] = data[word]
                        else:
                            if 'yagogeoentity' in type:
                                yagogeoentity[word] = data[word]
    topt = {}
    if bool(person):
        topt['person'] = person
    if bool(organization):
        topt['organization'] = organization
    if bool(event):
        topt['event'] = event
    if bool(artifact):
        topt['artifact'] = artifact
    if bool(yagogeoentity):
        topt['yagogeoentity'] = yagogeoentity
    return topt




class Similarity(Resource):
    def post(self):
        args = parser.parse_args()
        doc1 = nlp(args['doc1'])
        doc2 = nlp(args['doc2'])
        return doc1.similarity(doc2), 201, {'Access-Control-Allow-Origin': '*'}


class JSimilarity(Resource):
    def post(self):
        args = parser.parse_args()
        doc1 = args['doc1']
        doc2 = args['doc2']
        words_doc1 = set(doc1.lower().split()) 
        words_doc2 = set(doc2.lower().split())
        intersection = words_doc1.intersection(words_doc2)
        union = words_doc1.union(words_doc2)
        return float(len(intersection)) / len(union), 201, {'Access-Control-Allow-Origin': '*'}

class CosSimilarity(Resource):
    def post(self):
        args = parser.parse_args()
        X = nlp(args['doc1'])
        Y= nlp(args['doc2'])
        doc1 = nlp(X)
        doc2= nlp(Y)
        list1=[]
        list2=[]
        for token in doc1:
            if not token.is_stop and not token.is_punct and not token.text.isspace():
                list1.append(token.text)

        for token in doc2:
            if not token.is_stop and not token.is_punct and not token.text.isspace():
                list2.append(token.text)
        list1=set(list1)
        list2=set(list2)
        rvector = list1.union(list2)

        l1=[]
        l2=[]

        for w in rvector:
            if w in list1: l1.append(1) # create a vector
            else: l1.append(0)
            if w in list2: l2.append(1)
            else: l2.append(0)
        c = 0

        # cosine formula
        for i in range(len(rvector)):
            c+= l1[i]*l2[i]
        cosine = c / float((sum(l1)*sum(l2))**0.5)
        return cosine, 201, {'Access-Control-Allow-Origin': '*'}

class Temporality(Resource):
    def post(self):
        args = parser.parse_args()
        mot = args['mot']
        j=[]
        dates=[]
        for doc in data:
            for line in doc['ents']:
                if line['mot']==mot:
                    if len(line['type'])>0:
                        j.append(line['type'][0])
                        dates.append(doc['dateTime'])
                        break
                    else:
                        j.append(line['types'][0])
                        dates.append(doc['dateTime'])
        print(j)
        final=[]
        for i in range(0,len(j)):
            if i!=len(j)-1:
                t={'x':j[i],'y':[dates[i],dates[i+1]]}
            else:
                #b = time.localtime()
                #t={'x':j[i],'y':[dates[i],time.strftime("%Y-%m-%dT%H:%M:%SZ", b)]}
                time_str = dates[i]
                date_format_str = "%Y-%m-%dT%H:%M:%SZ"
                given_time = datetime.strptime(time_str, date_format_str)
                final_time = given_time + timedelta(hours=2)
                final_time_str = final_time.strftime('%Y-%m-%dT%H:%M:%SZ')
                t={'x':j[i],'y':[dates[i],final_time_str]}
            final.append(t)
        return final, 201, {'Access-Control-Allow-Origin': '*'}






class TopTypes(Resource):
    def post(self):
        args = parser.parse_args()
        text = args['content']
        table = getNER(text)
        ner = table[0]
        offsets=table[1]

        dicto={}
        for j in offsets:
            count=0
            for i in offsets:
                if i[0]==j[0]:
                    count=count+1
            dicto[j[0]]=count
        
        #types = getTypes(ner)
        types = getTypes(text)
        topt = orderByTopType(types)
        labels = []
        series = []
        for i in topt:
            labels.append(i)
            #series.append(len(topt[i]))
            count=0
            for j in topt[i]:
                count=count+dicto[j]
            series.append(count)

        return [labels, series], 201, {'Access-Control-Allow-Origin': '*'}






api.add_resource(TopTypes, '/getTopTypes')
api.add_resource(CosSimilarity, '/simCos')
api.add_resource(Similarity, '/simSpacy')
api.add_resource(JSimilarity, '/jSim')
api.add_resource(Temporality, '/temporality')


if __name__ == '__main__':
    app.run()
