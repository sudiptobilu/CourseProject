import string

import nltk
from nltk.tag.stanford import StanfordNERTagger
import sys, os
import re
import random
import json
import requests

sys.path.append(os.path.join(os.path.dirname(sys.path[0]), 'lib'))
sys.path.append(os.path.join(os.path.dirname(sys.path[0]), 'apps'))
sys.path.append(os.path.join(os.path.dirname(sys.path[0]), 'data'))

from apps.frontend.utils.beautiful_soup import get_js_soup, remove_script, close_driver
from apps.frontend.crawler.crawler import build_url
from apps.backend.utils.document import Document
from apps.backend.utils.facultydb import FacultyDB

dirname = os.path.dirname(__file__)
model_file = os.path.join(dirname,
                          '../../../lib/stanford-ner-2020-11-17/classifiers/english.all.3class.distsim.crf.ser.gz')
jar_file = os.path.join(dirname, '../../../lib/stanford-ner-2020-11-17/stanford-ner.jar')

st = StanfordNERTagger(model_file, jar_file, encoding='utf-8')


def validate_url(url):
    response = requests.get(url)
    if response.status_code > 200:
        return False
    return True

def random_str_generator(size=8, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def __do_db_call__(faculty_list):
    try:
        faculty_db = FacultyDB()
        faculty_db.add_records(faculty_list)
    except Exception as exc:
        raise Exception(" Database error occurred = {}".format(exc))


class ScrapeFacultyWebPage:
    def __init__(self, faculty_dict):
        self.faculty_dict = faculty_dict
        self.dept_url = self.faculty_dict.get('dept_url')
        self.base_url = self.faculty_dict.get('base_url')
        self.faculty_link = self.faculty_dict.get('faculty_link')
        self.faculty_link_soup = self.faculty_dict.get('faculty_link_soup')
        self.faculty_urls = []
        self.all_faculty_text = ''
        self.sanitized_list = []

    def get_faculty_urls(self):
        all_a_tags = list()
        # TODO - add more here
        div_class = ['content', 'container']
        if not self.faculty_link_soup:
            self.faculty_link_soup = remove_script(get_js_soup(self.faculty_link))
        unique_href = set()
        for cls in div_class:
            div_lst = self.__find_div__('class', cls)
            div_lst.extend(self.__find_div__('id', cls))
            all_a_tags.extend(self.__build_a_tags__(div_lst, unique_href))

        for tag in all_a_tags:
            # print('tag  => ', tag)
            tag_text = tag.text.strip()
            if tag_text:
                # print('text inside a tag => ', tag_text)
                self.all_faculty_text += tag_text + ' ~ '
        # print('all text ', self.all_faculty_text)
        self.__check_name__()
        # print('sanitized list ', self.sanitized_list)
        for tag in all_a_tags:
            link = tag["href"]
            tag_text = tag.text.strip()
            tag_text = re.sub("[^a-zA-Z0-9]+", "", tag_text)
            for name in self.sanitized_list:
                if name == tag_text and len(name):
                    faculty_profile_link = build_url(link, self.dept_url)
                    if validate_url(faculty_profile_link):
                        self.faculty_urls.append(faculty_profile_link)
                    else:
                        faculty_profile_link = build_url(link, self.faculty_link)
                        if validate_url(faculty_profile_link):
                            self.faculty_urls.append(faculty_profile_link)
                    break
        bio_dict = dict()
        for url in self.faculty_urls:
            try:
                bio_texts = self.get_bio(url)
                bio_dict[url] = bio_texts
            except:
                pass

        # process the document
        self.process_document(bio_dict)
        close_driver()

    def __build_a_tags__(self, div_tag_lst, unique_href):
        for div in div_tag_lst:
            a_tags = div.find_all("a")
            for tag in a_tags:
                href = tag.get("href")
                if href and 'mailto:' not in href and 'tel:' not in href and tag not in unique_href:
                    unique_href.add(tag)
                    yield tag

    def __find_div__(self, attr_to_search, text):
        return self.faculty_link_soup.find_all("div", recursive=True, attrs={attr_to_search: re.compile(text)})

    def __check_name__(self):
        print('-' * 20, 'Started NLTK validation for human names ', '-' * 20)
        for token in nltk.sent_tokenize(self.all_faculty_text):
            tokens = nltk.tokenize.word_tokenize(token)
            tags = st.tag(tokens)
            full_name = ''
            for tag in tags:
                # print('tag inside validate method ', tag)
                if tag[1] == 'PERSON':
                    full_name += tag[0]
                if tag[0] == '~':
                    full_name = re.sub("[^a-zA-Z0-9]+", "", full_name)
                    if len(full_name):
                        self.sanitized_list.append(full_name)
                    full_name = ''

    def get_bio(self, url):
        faculty_bio_soup = remove_script(get_js_soup(url))
        div_class = ['content', 'container']
        unique_href = set()
        all_texts = []
        for cls in div_class:
            elements = faculty_bio_soup.find_all(class_=cls)
            if not len(elements):
                elements = faculty_bio_soup.find_all(id=cls)
            for elem in elements:
                all_texts.extend(s.strip() for s in elem.strings if s.strip())

        return " ".join(all_texts)

    def process_document(self, bio_dict):
        faculty_dict_list = []
        count = 0
        print(f"{'*' * 50}")
        for i, url in enumerate(self.faculty_urls):
            print(f"Processing Faculty #{i+1}")
            print(f"Base URL (University URL: {self.base_url}")
            print(f"Department URL: {self.dept_url}")
            print(f"Faculty URL: {url}")
            try:
                faculty_dict = dict()
                bio = bio_dict.get(url)
                doc = Document(
                    doc=bio,
                    faculty_url=url,
                    department_url=self.dept_url,
                    university_url=self.base_url
                )
                faculty_dict['faculty_name'] = doc.extract_name()
                print(f'{count}, {faculty_dict["faculty_name"]} ')
                faculty_dict['faculty_department_name'] = doc.extract_department()
                faculty_dict['faculty_university_name'] = doc.extract_university()
                faculty_dict['faculty_phone'] = doc.extract_phone()
                faculty_dict['faculty_email'] = doc.extract_email()
                faculty_dict['faculty_expertise'] = doc.extract_expertise()
                faculty_dict['faculty_homepage_url'] = url
                faculty_dict['faculty_department_url'] = self.dept_url
                faculty_dict['faculty_university_url'] = self.base_url
                faculty_dict['faculty_biodata'] = bio
                faculty_dict['faculty_location'] = doc.extract_location()
                faculty_dict_list.append(faculty_dict)

            except Exception as e:
                print(f"(IGNORING) Exception encountered for Faculty URL: {url}", "\n", str(e))
                pass

            print(f"{'*' * 50}")

        print(__file__, ":: faculty_dict_list: ")
        faculty_list_json = json.dumps(faculty_dict_list)
        __do_db_call__(faculty_dict_list)


if __name__ == '__main__':
    faculty_dict = {
        'dept_url': "https://www.eecs.psu.edu/",
        'faculty_link': "https://www.eecs.psu.edu/departments/cse-faculty-list.aspx",
        'base_url': "https://www.psu.edu/",
    }
    scrapper = ScrapeFacultyWebPage(faculty_dict=faculty_dict)
    scrapper.get_faculty_urls()
    print('total faculty page found = ', len(scrapper.faculty_urls))
