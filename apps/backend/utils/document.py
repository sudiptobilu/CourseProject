import re, os, logging

from urllib import request

import gensim
import gensim.corpora as corpora
import nltk
from nltk.tag import StanfordNERTagger
from nltk.tokenize import word_tokenize
from bs4 import BeautifulSoup

# import guidedlda
# from sklearn.feature_extraction.text import CountVectorizer

from apps.backend.api.googleapi import GoogleAPI
from apps.backend.utils.nltk_utils import sanitizer, tokenizer, stopwords

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)
nltk.downloader.download('maxent_ne_chunker', quiet=True)
nltk.downloader.download('words', quiet=True)
nltk.downloader.download('treebank', quiet=True)
nltk.downloader.download('maxent_treebank_pos_tagger', quiet=True)

# logger = logging.getLogger('ExpertSearchv2.0')
logging.basicConfig(filename='lda_model.log', format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)



class Document:

    def __init__(self, doc, faculty_url=None, department_url=None, university_url=None):
        self.doc = doc
        self.faculty_url = faculty_url
        self.department_url = department_url
        self.university_url = university_url
        self.stop_words = stopwords.words('english')
        logger = logging.getLogger('my_module_name').setLevel(logging.WARNING)

    def __extract_ner(self, tag="PERSON"):
        """
        Using StanfordNERTagger finds name entity recognition
        :param tag:
        :return:
        """
        if not self.doc:
            return ""

        matched_tokens = []

        try:
            dirname = os.path.dirname(__file__)
            model_file = os.path.join(dirname,
                                      '../../../lib/stanford-ner-2020-11-17/classifiers/english.all.3class.distsim.crf.ser.gz')
            jar_file = os.path.join(dirname, '../../../lib/stanford-ner-2020-11-17/stanford-ner.jar')

            self.st = StanfordNERTagger(model_file, jar_file, encoding='utf-8')

            tokenized_text = word_tokenize(self.doc)
            classified_text = self.st.tag(tokenized_text)

            found_name = False
            name = ''
            for tup in classified_text:
                if found_name:
                    if tup[1] == tag:
                        name += ' ' + tup[0].title()
                    else:
                        break
                elif tup[1] == tag:
                    name += tup[0].title()
                    found_name = True

            matched_tokens.append(name)
        except Exception as e:
            print("Exception encouneted while extracting name: " + str(e))
            pass

        return " ".join(matched_tokens)

    def extract_expert_ner(self):
        """
        Using StanfordNERTagger finds name entity recognition
        """
        if not self.doc:
            return ""

        matched_tokens = []

        try:
            dirname = os.path.dirname(__file__)
            model_file = os.path.join(dirname,
                                      '../../../lib/stanford-ner-2020-11-17/classifiers/english.all.3class.distsim.crf.ser.gz')
            jar_file = os.path.join(dirname, '../../../lib/stanford-ner-2020-11-17/stanford-ner.jar')

            st = StanfordNERTagger(model_file, jar_file, encoding='utf-8')

            tokenized_text = word_tokenize(self.doc)
            classified_text = st.tag(tokenized_text)

            noname = ''
            for tup in classified_text:
                if tup[1] != 'PERSON':
                    noname += ' ' + tup[0].title()

            matched_tokens.append(noname)
        except Exception as e:
            print("Exception encouneted while extracting nonames: " + str(e))
            pass

        return " ".join(matched_tokens)

    def __extract_title(self, url):
        if not url:
            return ""

        html = request.urlopen(url).read().decode('utf8')

        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('title')

        title = title.string if title else ""
        title =  title.split('|')[1].strip() if title and "|" in title else title if title else ""
        return title

    def extract_expertise(self):

        if not self.doc:
            return ""

        tokens = tokenizer(doc.extract_expert_ner())
        #tokens = tokenizer(self.doc)
        # print("tokens: ", tokens)

        # Create Dictionary
        id2word = corpora.Dictionary([tokens])

        # Create Corpus - # Term Document Frequency
        corpus = [id2word.doc2bow(tokens)]

        # Build LDA model
        lda_model = gensim.models.ldamodel.LdaModel(corpus=corpus,
                                                    id2word=id2word,
                                                    num_topics=1,
                                                    random_state=10,
                                                    update_every=1,
                                                    chunksize=1,
                                                    passes=50,
                                                    alpha='auto',
                                                    per_word_topics=True)

        """
        # Print the Keyword in the 10 topics
        print(lda_model.print_topics())
        doc_lda = lda_model[corpus]
        """

        topics = lda_model.print_topics(num_words=10)
        lda_model.save("cs410_project")

        '''for topic in topics:
            print(topic)'''


        shown_topics = lda_model.show_topics(num_topics=1,
                                             num_words=10,
                                             formatted=False)
        topic_list = [[word[0] for word in topic[1]] for topic in shown_topics]

        # LDA topics
        """seed_topic_list = [[word[0] for word in topic[1]] for topic in shown_topics]
        #seed_topic_list = [["internet","education","research"]]

        # print("LDA Topics: ", seed_topic_list)
        token_vectorizer = CountVectorizer(tokenizer=tokenizer,
                                           min_df=1,
                                           max_df=1.0,
                                           ngram_range=(1, 4))
        X = token_vectorizer.fit_transform([self.doc])
        tf_feature_names = token_vectorizer.get_feature_names()
        word2id = dict((v, idx) for idx, v in enumerate(tf_feature_names))
        model = guidedlda.GuidedLDA(n_topics=1, n_iter=100, random_state=7, refresh=10)
        seed_topics = {}
        for t_id, st in enumerate(seed_topic_list):
            for word in st:
                seed_topics[word2id[word]] = t_id
        model.fit(X, seed_topics=seed_topics, seed_confidence=0.15)
        n_top_words = 10
        topic_words = []
        for i, topic_dist in enumerate(model.topic_word_):
            topic_words = np.array(tf_feature_names)[np.argsort(topic_dist)][:-(n_top_words + 1):-1]
            # print('Topic {}: {}'.format(i, ' '.join(topic_words)))
        # return unqiue topic words
        return " ".join(list(set(" ".join(topic_words).split())))

        # return unqiue topic words
        # return " ".join(list(set(seed_topic_list)))
        """

        return " ".join(topic_list[0]) if topic_list and topic_list[0] else None

    def extract_phone(self):
        if not self.doc:
            return ""

        # phone_numbers = re.findall(r'[+(]?[1-9][0-9 .\-()]{8,}[0-9]', self.doc)
        phone_numbers = re.findall(r"\(?\b[2-9][0-9]{2}\)?[-. ]?[2-9][0-9]{2}[-. ]?[0-9]{4}\b", self.doc)
        return phone_numbers[0] if phone_numbers else None

    def extract_email(self):
        if not self.doc:
            return ""

        emails = re.findall(r'[\w.-]+@[\w.-]+', self.doc)
        return emails[0] if emails else None

    def extract_name(self):
        # name = self.__extract_ner(tag="PERSON")
        name = self.__extract_title(self.faculty_url)
        return name if name else None

    def extract_university(self):
        university_name = self.__extract_title(self.university_url)
        return university_name if university_name else None

    def extract_department(self):
        department_name =  self.__extract_title(self.department_url)
        return department_name if department_name else None

    def extract_biodata(self):
        return " ".join(sanitizer(self.doc)) if self.doc else None

    def extract_location(self):
        location = ""
        try:
            googleAPI = GoogleAPI(place_name=self.extract_university())
            comps = googleAPI.get_component(field_comp='address_components')
            for comp in comps:
                if len(comp['types']) > 1:
                    if comp['types'][0] == 'administrative_area_level_1':
                        state = comp['long_name']
                        location = location + str(comp['long_name']) + ", "
                    if comp['types'][0] == 'locality':
                        city = comp['long_name']
                        location = location + str(comp['long_name']) + ", "
                    if comp['types'][0] == 'country':
                        country = comp['long_name']
                        location = location + str(comp['long_name'])
        except:
            pass

        return location if location else "Unknown"


if __name__ == '__main__':
    #doc = "  Geoffrey Werner Challen Teaching Associate Professor 2227 Siebel Center for Comp Sci 201 N. Goodwin Ave. Urbana Illinois 61801 (217) 300-6150 challen@illinois.edu : Primary Research Area CS Education Research Areas CS Education For more information blue Systems Research Group (Defunct) Internet Class: Learn About the Internet on the Internet OPS Class: Learn Operating Systems Online CS 125 Home Page Education Ph.D. Computer Science, Harvard University, 2010 AB Physics, Harvard University, 2003 Academic Positions Associate Teaching Professor, University of Illinois, 2017 . Primary Research Area CS Education Research Areas CS Education For more information blue Systems Research Group (Defunct) Internet Class: Learn About the Internet on the Internet OPS Class: Learn Operating Systems Online CS 125 Home Page . . For more information blue Systems Research Group (Defunct) Internet Class: Learn About the Internet on the Internet OPS Class: Learn Operating Systems Online CS 125 Home Page . "
    doc = "  Geoffrey Werner Challen Teaching Associate Professor 2227 Siebel Center for Comp Sci 201 N. Goodwin Ave. Urbana Illinois 61801 (217) 300-6150 challen@illinois.edu : Primary Research Area CS Education Research Areas CS Education For more information blue Systems Research Group (Defunct) Internet Class: Learn About the Internet on the Internet OPS Class: Learn Operating Systems Online CS 125 Home Page Education Ph.D. Computer Science, Harvard University, 2010 AB Physics, Harvard University, 2003 Academic Positions Associate Teaching Professor, University of Illinois, 2017 . Primary Research Area CS Education Research Areas CS Education For more information blue Systems Research Group (Defunct) Internet Class: Learn About the Internet on the Internet OPS Class: Learn Operating Systems Online CS 125 Home Page . . For more information blue Systems Research Group (Defunct) Internet Class: Learn About the Internet on the Internet OPS Class: Learn Operating Systems Online CS 125 Home Page . Jiaxin Lin , Kiran Patel , Brent E. Stephens , Anirudh Sivaraman , Aditya Akella Jiaxin Lin , Kiran Patel , Brent E. Stephens , Anirudh Sivaraman , Aditya Akella Jiaxin Lin , Kiran Patel , Brent E. Stephens , Anirudh Sivaraman , Aditya Akella Jiaxin Lin , Kiran Patel , Brent E. Stephens , Anirudh Sivaraman , Aditya Akella"
    doc = Document(doc,
                   faculty_url="http://www.cs.utah.edu/~mflatt/",
                   department_url="https://www.eecs.psu.edu/departments/cse-faculty-list.aspx",
                   university_url="https://utah.edu/")

    # department_url = "https://www.cs.utah.edu/",
    print("NAME:       ", doc.extract_name())
    print("DEPARTMENT: ", doc.extract_department())
    """
    print("UNIVERSITY: ", doc.extract_university())
    print("PHONE:      ", doc.extract_phone())
    print("EMAIL:      ", doc.extract_email())
    print("EXPERTISE:  ", doc.extract_expertise())
    print("LOCATION:   ", doc.extract_location())
    print("BIODATA:    ", doc.extract_biodata())
    """
    print("EXPERTISE:  ", doc.extract_expertise())