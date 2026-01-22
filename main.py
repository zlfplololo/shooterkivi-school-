from kivymd.app import MDApp
from kivymd.uix.widget import MDWidget
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy import platform
from kivy.uix.image import Image
from random import randint
from kivymd.uix.button import MDFlatButton
from kivymd.uix.dialog import MDDialog
from kivy.core.window import Keyboard
from kivy.properties import NumericProperty
from kivymd.uix.floatlayout import MDFloatLayout
from kivymd.uix.fitimage import FitImage


FPS = 60
BULLET_SPEED = dp(10)
Mine_SPEED = dp(1)
SHIP_SPEED = dp(5)
DIR_UP = 1
DIR_DOWN = -1

dundun = 1

SPAWN_ENEMY_TIME = 2

HP_DEF = 3

FIRE_RATE_MIN = 0.5
FIRE_RATE_MEDIUM = 2
FIRE_RATE_DEF = FIRE_RATE_MIN

class Shot(MDWidget):
    def __init__(self, direction, owner, **kwargs):
        super().__init__(**kwargs)
        self.direction = direction
        self.owner = owner  # хто стріляв (гравець або ворог)

class Mine(Image):
    def __init__(self, direction, owner, time, acceleration, **kwargs):
        super().__init__(**kwargs)
        self.direction = direction
        self.owner = owner
        self.time = time
        self.acceleration = acceleration


class Ship(Image):
    hp = NumericProperty()
    max_hp = NumericProperty()

    def __init__(self, direction=DIR_UP, hp=HP_DEF, fire_rate = FIRE_RATE_MEDIUM,**kwargs):
        super().__init__(**kwargs)
        self.direction = direction
        self.hp = self.max_hp = hp
        # Швидкострільність
        self.fire_rate = fire_rate
        self._last_shot = self.fire_rate

    def moveLeft(self):
        self.pos[0] -= SHIP_SPEED

    def moveRight(self):
        self.pos[0] += SHIP_SPEED

    def shot(self):
        shot = Shot(self.direction, owner=self)
        shot.center_x = self.center_x
        shot.y = self.top if self.direction == DIR_UP else self.y - shot.height
        self.parent.parent.parent.parent.bullets.append(shot)
        self.parent.add_widget(shot)

        self._last_shot = 0

    def update(self, dt):
        self._last_shot += dt


class PlayerShip(Ship):
    def __init__(self, **kwargs):
        super().__init__(direction=DIR_UP, fire_rate=FIRE_RATE_MIN, **kwargs)

    def update(self, dt, keys):
        super().update(dt)

        for key in keys:
            if keys[key]:
                if key == 'left' and self.center_x > 0:
                    self.moveLeft()
                if key == 'right' and self.center_x < Window.width:
                    self.moveRight()
                if key == 'shot':
                    if self._last_shot >= self.fire_rate:
                        self.shot()
                    keys[key] = False
                if key == 'mina':
                    if self._last_shot >= self.fire_rate:
                        self.throwmine()
                    keys[key] = False
    def throwmine(self):
        mine = Shot(self.direction, owner=self, time=10, acceleration=5)
        mine.center_x = self.center_x
        mine.y = self.top if self.direction == DIR_UP else self.y - shot.height
        self.parent.parent.parent.parent.mines.append(mine)
        self.parent.add_widget(mine)


class EnemyShip(Ship):
    def __init__(self, **kwargs):
        super().__init__(direction=DIR_DOWN, **kwargs)


    def update(self, dt):
        super().update(dt)

        self.y -= dp(3)
        
        if self._last_shot >= self.fire_rate:
            self.shot()

# Фон з прокруткою для створення паралакс-ефекту
class MoveBackground(MDFloatLayout):
    def __init__(self, source, speed=dp(1), scale=1, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speed = speed
        self.add_widget(FitImage(source=source, size_hint_y=scale))
        self.add_widget(FitImage(source=source, size_hint_y=scale, pos=(0, Window.size[1] * scale)))

    def move(self):
        for img in self.children:
            img.pos[1] -= self.speed
            if img.top <= 0:
                img.pos[1] = img.size[1]


class GameScreen(MDScreen):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.eventkeys = {}
        self.ship = None
        self.enemyShips = []

        self.bullets = []
        self.mines = []

        self.pauseMenu = None

        # Для спавну ворожих кораблів
        self.spawn_delay = SPAWN_ENEMY_TIME
        self.time_last_spawn = 0

        # Додавання на задній план картинок з прокруткою
        self.backBack = MoveBackground(source='assets/images/cosmos.jpg', speed=0.2)
        self.backFront = MoveBackground(source='assets/images/planets.png', speed=1, scale=3)

        self.ids.back.add_widget(self.backBack)
        self.ids.back.add_widget(self.backFront)

        # Керування з клавіатури під час тестування з комп'ютера
        Window.bind(on_key_down=self._on_key_down)
        Window.bind(on_key_up=self._on_key_up)

    def on_enter(self, *args):
        self.updateEvent = Clock.schedule_interval(self.update, 1 / FPS)
        # головний корабель
        self.ship = self.ids.ship
        self.ship.hp = self.ship.max_hp

        return super().on_enter(*args)

    def spawn_enemy(self):
        enemy = EnemyShip()  
        enemy.pos = (randint(0, int(Window.width - enemy.width)), Window.height)
        self.enemyShips.append(enemy)
        self.ids.front.add_widget(enemy)

    def update(self, dt):
        # головний корабель
        self.ship.update(dt, self.eventkeys)

        # вороги - спавн кожні [self.spawn_delay] секунд
        self.time_last_spawn += dt
        if self.time_last_spawn >= self.spawn_delay:
            self.spawn_enemy()
            self.time_last_spawn = 0

        # вороги - рух
        for ship in self.enemyShips[:]:
            ship.update(dt)
            if ship.top < 0:
                self.enemyShips.remove(ship)
                self.ids.front.remove_widget(ship)

            # колізія з гравцем 
            if ship.collide_widget(self.ship):
                self.game_over()

        # кулі
        self.manage_bullets()

        # Прокрутка фону
        self.backBack.move()
        self.backFront.move()

    def manage_bullets(self):
        for bullet in self.bullets[:]:
            bullet.y += BULLET_SPEED * bullet.direction

            # Перевірка колізії
            self.check_collisions(bullet)
            
            # Перевірка виходу за рамки вікна
            if bullet.top < 0 or bullet.y > Window.height:
                self.remove_bullet(bullet)
        for mine in self.mines[:]:
            mine.y += Mine_SPEED * mine.direction * mine.acceleration
            mine.acceleration -= 0.1
            mine.time -= dt
            if mine.time <= 0:
                pass

    def check_collisions(self, bullet):
        if bullet.owner == self.ship:
            # перевіряємо потрапляння у ворога
            for enemy in self.enemyShips[:]:
                if bullet.collide_widget(enemy):
                    enemy.hp -= 1
                    if enemy.hp <= 0:
                        self.enemyShips.remove(enemy)
                        self.ids.front.remove_widget(enemy)

                    self.remove_bullet(bullet)
                    break
        else:
            # перевіряємо потрапляння у гравця
            if bullet.collide_widget(self.ship):
                self.ship.hp -= 1
                print(self.ship.hp)

                if self.ship.hp <= 0:
                    self.game_over()

                self.remove_bullet(bullet)

    def remove_bullet(self, bullet):
        if bullet in self.bullets:
            self.bullets.remove(bullet)
            self.ids.front.remove_widget(bullet)

    def game_over(self):
        self.updateEvent.cancel()
        # Видалення ворогів
        for enemy in self.enemyShips[:]:
            self.enemyShips.remove(enemy)
            self.ids.front.remove_widget(enemy)
        # Видалення куль
        for bullet in self.bullets[:]:
            self.ids.front.remove_widget(bullet)
            self.bullets.remove(bullet)

        self.manager.current = 'game_over'

    def pressKey(self, key):
        self.eventkeys[key] = True

    def releaseKey(self, key):
        self.eventkeys[key] = False

    def show_menu(self):
        self.updateEvent.cancel()
        
        if not self.pauseMenu:
            self.pauseMenu = MDDialog(
                title="Game Paused",
                text="Resume the game?",
                on_dismiss=self.resumeGame,
                buttons=[
                    MDFlatButton(
                        text="RESUME",
                        theme_text_color="Custom",
                        text_color=app.theme_cls.primary_color,
                        on_press=self.pauseStop
                    )
                ],
            )
        self.pauseMenu.open()

    def pauseStop(self, *args):
        self.pauseMenu.dismiss()

    def resumeGame(self, *args):
        self.updateEvent = Clock.schedule_interval(self.update, 1 / FPS)
    
    # Керування з клавіатури під час тестування з комп'ютера
    def _on_key_down(self, window, keycode, *args, **kwargs):
        key = key if (key := Keyboard.keycode_to_string(window, keycode)) != 'spacebar' and (key := Keyboard.keycode_to_string(window, keycode)) != 'e' else 'shot' if (key := Keyboard.keycode_to_string(window, keycode)) != 'e' else 'mine'
        self.eventkeys[key] = True

    def _on_key_up(self, window, keycode, *args, **kwargs):
        key = key if (key := Keyboard.keycode_to_string(window, keycode)) != 'spacebar' and (key := Keyboard.keycode_to_string(window, keycode)) != 'e' else 'shot' if (key := Keyboard.keycode_to_string(window, keycode)) != 'e' else 'mine'
        self.eventkeys[key] = False


class GameOverScreen(MDScreen):
    pass


class MainScreen(MDScreen):
    pass


class ShooterApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Purple"

        self.sm = MDScreenManager()

        self.sm.add_widget(MainScreen(name='main'))
        self.sm.add_widget(GameScreen(name='game'))
        self.sm.add_widget(GameOverScreen(name='game_over'))

        return self.sm


if platform != 'android':
    Window.size = (450, 900)
    Window.top = 100
    Window.left = 600

app = ShooterApp()
app.run()
