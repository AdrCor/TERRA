import time
from client import client
from model import Geo

class PracticeProgress:
    
    @staticmethod
    def get_progress(id_user: str, region: str) -> int:
        response = client.table('practice_progress').select('*').match({'id_user': id_user, 'region': region}).execute()
        if not response.data:
            return PracticeProgress.init_progress(id_user, region)
        return response.data[0]['progress']
    
    @staticmethod
    def init_progress(id_user: str, region: str) -> int:
        response = client.table('practice_progress').insert({'id_user': id_user, 'region': region, 'progress': 5}).execute()
        return response.data[0]['progress']
    
    @staticmethod
    def update_progress(id_user: str, region: str, value: int) -> int:
        response = client.table('practice_progress').update({'progress': value}).match({'id_user': id_user, 'region': region}).execute()
        return response.data[0]['progress']

    @staticmethod
    def delete_all(id_user):
        response = client.table('practice_progress').delete().eq('id_user', id_user).execute()


class PracticeGrade:

    @staticmethod
    def init_grades(id_user: str, region: str):
        countries = [dic['country'] for dic in Geo.get_by_region(region)]
        response = client.table('practice_grade').upsert({
            'id_user': id_user,
            region: {country: {'count': 0, 'reaction': 0, 'typing': 0, 'score': 0} for country in countries}
            }).execute()
        return response.data[0][region]
    
    @staticmethod
    def set_grades(id_user: str, region: str, grades: dict):
        response = client.table('practice_grade').upsert({
            'id_user': id_user,
            region: grades
            }).execute()
        return response.data[0][region]

    @staticmethod
    def get_grades(id_user: str, region: str):
        response = client.table('practice_grade').select(region).execute()
        if not response.data or not response.data[0][region]:
            return PracticeGrade.init_grades(id_user, region)
        return response.data[0][region]
    
    
    @staticmethod
    def get_data(id_user: str, region: str):

        data = Geo.get_by_region(region)
        progress = PracticeProgress.get_progress(id_user, region)
        grades = PracticeGrade.get_grades(id_user, region)

        if progress == PracticeGrade.get_progress_from_grades(grades):
            progress = PracticeProgress.update_progress(id_user, region, progress + 5)

        for index, obj in enumerate(data):
            obj['grades'] = grades[obj['country']]
            obj['unlocked'] = index < progress

        return data
    
    @staticmethod
    def get_progress_from_grades(grades: dict) -> int:
        scores = [grade['score'] for grade in grades.values() if grade['score'] >= 50]
        if len(scores) == len(grades):
            return -1
        return len(scores)
        
    
    @staticmethod
    def update_grades(id_user: str, region: str, data: list[dict]):
        # data = [{'country': 'France', 'reaction': 823, 'typing': 300}]
        t1 = time.perf_counter()
        grades = PracticeGrade.get_grades(id_user, region)
        t2 = time.perf_counter()

        for entry in data:
            current_rating = grades[entry['country']]
            grades[entry['country']] = PracticeGrade.get_new_grades(current_rating, entry)
        t3 = time.perf_counter()
        PracticeGrade.set_grades(id_user, region, grades)
        t4 = time.perf_counter()
        data = PracticeGrade.get_data(id_user, region)
        t5 = time.perf_counter()
        print('upade grades = ', t4 - t1)
        print('--get grades = ', t2 - t1)
        print('--get_new_grades = ', t3 - t2)
        print('--set_grades = ', t4 - t3)
        print('--get_data = ', t5 - t4)
        return data
    
    @staticmethod
    def get_new_grades(current_rating: dict, entry: dict):

        if not entry['valid']:
            entry['reaction'] = 10000
            entry['typing'] = 0
        entry['reaction'] = min(entry['reaction'], 10000)

        if current_rating['count'] == 0:
            count = 1
            typing = entry['typing']
            reaction = entry['reaction']
            score = int(PracticeGrade.calculate_score(reaction, typing) / 5)
            return {'count': count, 'typing': typing, 'reaction': reaction, 'score': score}

        if current_rating['count'] < 10:
            count = current_rating['count'] + 1
            typing = int((current_rating['typing'] * current_rating['count'] + entry['typing']) / count)
            reaction = int((current_rating['reaction'] * current_rating['count'] + entry['reaction']) / count)
            score = int(PracticeGrade.calculate_score(reaction, typing) * min(count, 5) / 5)
            return {'count': count, 'typing': typing, 'reaction': reaction, 'score': score}
        
        else:
            count = current_rating['count'] + 1
            typing = int((current_rating['typing'] * 9 + entry['typing']) / 10)
            reaction = int((current_rating['reaction'] * 9 + entry['reaction']) / 10)
            score = PracticeGrade.calculate_score(reaction, typing)
            return {'count': count, 'typing': typing, 'reaction': reaction, 'score': score}


    @staticmethod
    def calculate_score(reaction: int, typing: int):
        score_reaction = PracticeGrade.calculate_reaction_score(reaction)
        score_typing = PracticeGrade.calculate_typing_score(typing)
        return min(int(score_reaction + score_typing), 100)
    
    @staticmethod
    def delete_all(id_user):
        response = client.table('practice_grade').delete().eq('id_user', id_user).execute()

    @staticmethod
    def calculate_reaction_score(reaction: int):
        reaction = min(max(reaction, 600), 4000)
        if reaction >= 2000:
            return int(-reaction / 80 + 50)
        if reaction >= 700:
            return int(-reaction / 52 + 63.46)
        else:
            return int(-reaction / 20 + 85)

    @staticmethod
    def calculate_typing_score(typing: int):
        typing = min(typing, 750)
        if typing <= 150:
            return int(typing / 6)
        if typing <= 500:
            return int(typing / 14 + 14.29)
        else:
            return int(typing / 50 + 40)