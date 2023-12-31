import vk_api
import data_store
from sqlalchemy import create_engine
from vk_api.longpoll import VkEventType, VkLongPoll
from vk_api.utils import get_random_id
from config import acces_token, comunity_token, db_url_object
from core import VkTools

class BotInterface():
    def __init__(self, comunity_token, access_token, engine):
        self.vk = vk_api.VkApi(token=comunity_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_tools = VkTools(access_token)
        self.params = {}
        self.worksheets = []
        self.offset = 0


    def message_send(self, user_id, message, attachment=None):
        self.vk.method('messages.send',
                        {'user_id': user_id,
                        'message': message,
                        'attachment': attachment,
                        'random_id': get_random_id(),})

    def get_user_photo(self, user_id):
        photos = self.vk_tools.get_photos(user_id)
        photo_string = ''
        for photo in photos:
            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
        return photo_string

    def event_handler(self):
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                command = event.text.lower()

                if command == 'привет' or command == 'старт' or command == 'начать' or command == 'пуск':
                    self.params = self.vk_tools.get_profile_info(event.user_id)
                    self.message_send(event.user_id,
                                      f'Здравствуй, {self.params["name"]}. \n Я помогу тебе найти идеальную пару ВКонтакте. \n Для получения списка команд напиши слово "команды".')

                elif command == 'команды' or command == 'команда':
                    self.message_send(event.user_id,
                                      'Команды: \n бот- запуск анализа твоего профиля \n показать анкету - показываем подходящие анкеты \n следующая - листаем анкеты \n завершить - завершение работы бота')

                elif command == 'бот':
                    self.message_send(event.user_id, 'Запускаю анализ твоего профиля.')
                    if self.params.get("city") is None:
                        self.message_send(event.user_id,
                                          'Укажите Ваш город в формате "город <название>"\n например "город Москва".')
                        continue
                    elif self.params.get("bdate") is None:
                        self.message_send(event.user_id,
                                          'Укажите Ваш возраст в формате "возраст <число>"\n например "возраст 18".')
                        continue
                    else:
                        self.message_send(event.user_id,
                                          'Город и возраст записали из твоей анкеты.\n Для просмотра анкет напиши команду показать анкеты')

                elif command.startswith("город "):
                    city_name = ' '.join(event.text.lower().split()[1:])
                    city = self.vk_tools.__class__(city_name)
                    if city is None:
                        self.message_send(event.user_id, 'Такого города нет. :(')
                    else:
                        self.params['city'] = self.vk_tools.__class__(city_name)
                        self.message_send(event.user_id,
                                          f'город установлен.\n Для просмотра анкет напиши команду показать анкеты')

                elif command.startswith("возраст "):
                    age = event.text.lower().split()[1]
                    try:
                        age = int(age)
                    except ValueError:
                        self.message_send(event.user_id, 'Необходимо ввести число')
                        continue
                    if not 18 <= age <= 99:
                        self.message_send(event.user_id, 'Ваш возраст должен быть от 18 до 99 лет')
                        continue
                    self.params['bdate'] = age
                    self.message_send(event.user_id,
                                      'Возраст установлен.\n Для просмотра анкет напиши команду показать анкеты')

                elif command == 'показать анкеты' or command == 'показать анкету' or command == 'п':
                    if self.worksheets:
                        worksheet = self.worksheets.pop()
                        photos = self.vk_tools.get_photos(worksheet['id'])
                        photo_string = ''
                        for photo in photos:
                            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
                    else:
                        self.worksheets = self.vk_tools.search_worksheet(self.params, self.offset)
                        worksheet = self.worksheets.pop()
                        photos = self.vk_tools.get_photos(worksheet['id'])
                        photo_string = ''
                        for photo in photos:
                            photo_string += f'photo{photo["owner_id"]}_{photo["id"]},'
                        self.offset += 10
                    self.message_send(event.user_id, f'имя: {worksheet["name"]} ссылка: vk.com/{worksheet["id"]}',
                                      attachment=photo_string)

                    if not data_store.check_user(engine, event.user_id, worksheet["id"]):
                        data_store.add_user(engine, event.user_id, worksheet["id"])

                elif command == 'пока' or command == "нет" or command == "стоп" or command == "завершить" or command == "закончить" or command == "конец":
                    self.message_send(event.user_id,
                                      'Завершаю работу.')

                else:
                    self.message_send(event.user_id,
                                      'Для общения со мной нужно использовать специальные команды. Список команд для обшения со мной можно получить написав слово команды.')

if __name__ == '__main__':
    engine = create_engine(db_url_object)
    bot_interface = BotInterface(comunity_token, acces_token, engine)
    bot_interface.event_handler()