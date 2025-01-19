#!/usr/bin/env python
#-*- coding: utf-8 -*-

# Very simple tetris implementation
# 
# Control keys:
# Down - Drop stone faster
# Left/Right - Move stone
# Up - Rotate Stone clockwise
# Escape - Quit game
# P - Pause game
#
# Have fun!

# Copyright (c) 2010 "Kevin Chabowski"<kevin@kch42.de>
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

#!/usr/bin/env python
#-*- coding: utf-8 -*-

import sys
import time
from random import randrange as rand

import pygame
import cv2
import mediapipe as mp

# ------------------------------------------------------------------
# TETRIS CONFIG
# ------------------------------------------------------------------
config = {
    'cell_size':  20,
    'cols':       10,  # typical Tetris width
    'rows':       20,  # typical Tetris height
    'delay':      500, # ms between automatic piece drops
    'maxfps':     30
}

colors = [
    (0,   0,   0),     # dummy (index 0)
    (255, 0,   0),     # 1
    (0,   150, 0),     # 2
    (0,   0,   255),   # 3
    (255, 120, 0),     # 4
    (255, 255, 0),     # 5
    (180, 0,   255),   # 6
    (0,   220, 220)    # 7
]

tetris_shapes = [
    [[1, 1, 1],
     [0, 1, 0]],

    [[0, 2, 2],
     [2, 2, 0]],

    [[3, 3, 0],
     [0, 3, 3]],

    [[4, 0, 0],
     [4, 4, 4]],

    [[0, 0, 5],
     [5, 5, 5]],

    [[6, 6, 6, 6]],

    [[7, 7],
     [7, 7]]
]

# ------------------------------------------------------------------
# HELPER FUNCTIONS
# ------------------------------------------------------------------
def rotate_clockwise(shape):
    return [
        [ shape[y][x] for y in range(len(shape)) ]
        for x in range(len(shape[0]) - 1, -1, -1)
    ]

def check_collision(board, shape, offset):
    off_x, off_y = offset
    for cy, row in enumerate(shape):
        for cx, cell in enumerate(row):
            if cell:
                if (cx + off_x < 0 or 
                    cx + off_x >= config['cols'] or
                    cy + off_y >= config['rows'] or
                    board[cy + off_y][cx + off_x]):
                    return True
    return False

def remove_row(board, row):
    del board[row]
    return [[0 for _ in range(config['cols'])]] + board

def join_matrices(mat1, mat2, mat2_off):
    off_x, off_y = mat2_off
    for cy, row in enumerate(mat2):
        for cx, val in enumerate(row):
            if val:
                mat1[cy + off_y][cx + off_x] = val
    return mat1

def new_board():
    return [
        [0 for _ in range(config['cols'])] 
        for _ in range(config['rows'])
    ]

def add_garbage(board, lines):
    """Send garbage lines to the *bottom* of the board with a random hole."""
    from random import randrange
    if lines <= 0:
        return board
    for _ in range(lines):
        hole = randrange(config['cols'])
        new_row = [1]*config['cols']
        new_row[hole] = 0
        board.pop(0)
        board.append(new_row)
    return board

# ------------------------------------------------------------------
# TETRIS CLASS
# ------------------------------------------------------------------
class Tetris2P:
    def __init__(self):
        pygame.init()
        pygame.key.set_repeat(250, 25)
        pygame.display.set_caption("2-Player Tetris w/ CV Hand Gestures")

        # Tetris surfaces
        self.screen_width  = config['cell_size'] * config['cols'] * 2 + 40
        self.screen_height = config['cell_size'] * config['rows']
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))

        # Setup a timer for dropping pieces
        pygame.time.set_timer(pygame.USEREVENT + 1, config['delay'])

        # Create boards
        self.board1 = new_board()
        self.board2 = new_board()

        # Create first stones
        self.new_stone_p1()
        self.new_stone_p2()

        # State
        self.paused      = False
        self.gameover_p1 = False
        self.gameover_p2 = False
        self.b2b_p1      = False  # track back-to-back Tetrises
        self.b2b_p2      = False

        # -----------------------
        # Initialize camera + Mediapipe
        # -----------------------
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

        self.mp_hands = mp.solutions.hands
        self.hands_detector = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # up to two hands if needed
            min_detection_confidence=0.8,
            min_tracking_confidence=0.5
        )
        self.mp_drawing = mp.solutions.drawing_utils

        # Track if we have an "up" press locked to avoid spamming
        self.p1_is_pointing = False
        self.p2_is_pointing = False

    # ----------------------------------------------------------------
    # Stone Management
    # ----------------------------------------------------------------
    def new_stone_p1(self):
        self.stone1 = tetris_shapes[rand(len(tetris_shapes))]
        self.stone1_x = config['cols'] // 2 - len(self.stone1[0]) // 2
        self.stone1_y = 0
        if check_collision(self.board1, self.stone1, (self.stone1_x, self.stone1_y)):
            self.gameover_p1 = True

    def new_stone_p2(self):
        self.stone2 = tetris_shapes[rand(len(tetris_shapes))]
        self.stone2_x = config['cols'] // 2 - len(self.stone2[0]) // 2
        self.stone2_y = 0
        if check_collision(self.board2, self.stone2, (self.stone2_x, self.stone2_y)):
            self.gameover_p2 = True

    # ----------------------------------------------------------------
    # Drawing
    # ----------------------------------------------------------------
    def draw_matrix(self, matrix, offset=(0,0)):
        off_x, off_y = offset
        for y, row in enumerate(matrix):
            for x, val in enumerate(row):
                if val:
                    pygame.draw.rect(
                        self.screen,
                        colors[val],
                        pygame.Rect(
                            (off_x + x)*config['cell_size'],
                            (off_y + y)*config['cell_size'],
                            config['cell_size'], config['cell_size']
                        ),
                        0
                    )

    def center_msg(self, msg, offset_x, offset_y):
        font = pygame.font.Font(pygame.font.get_default_font(), 18)
        lines = msg.splitlines()
        for i, line in enumerate(lines):
            msg_image = font.render(line, False, (255,255,255), (0,0,0))
            w, h = msg_image.get_size()
            self.screen.blit(msg_image, (offset_x - w//2, offset_y - h//2 + i*22))

    # ----------------------------------------------------------------
    # Player 1 Moves
    # ----------------------------------------------------------------
    def move_p1(self, delta_x):
        if not self.gameover_p1 and not self.paused:
            new_x = self.stone1_x + delta_x
            if new_x < 0:
                new_x = 0
            if new_x > config['cols'] - len(self.stone1[0]):
                new_x = config['cols'] - len(self.stone1[0])
            if not check_collision(self.board1, self.stone1, (new_x, self.stone1_y)):
                self.stone1_x = new_x

    def rotate_p1(self):
        if not self.gameover_p1 and not self.paused:
            new_stone = rotate_clockwise(self.stone1)
            if not check_collision(self.board1, new_stone, (self.stone1_x, self.stone1_y)):
                self.stone1 = new_stone

    def drop_p1(self):
        if not self.gameover_p1 and not self.paused:
            self.stone1_y += 1
            if check_collision(self.board1, self.stone1, (self.stone1_x, self.stone1_y)):
                self.stone1_y -= 1
                self.board1 = join_matrices(self.board1, self.stone1, (self.stone1_x, self.stone1_y))
                lines_cleared = 0
                while True:
                    for i, row in enumerate(self.board1):
                        if 0 not in row:
                            self.board1 = remove_row(self.board1, i)
                            lines_cleared += 1
                            break
                    else:
                        break
                # Garbage logic
                if lines_cleared > 0:
                    if lines_cleared == 4:  # Tetris
                        garbage = 4
                        if self.b2b_p1:
                            garbage += 1
                        self.b2b_p1 = True
                    else:
                        garbage = lines_cleared - 1
                        self.b2b_p1 = False
                    self.board2 = add_garbage(self.board2, garbage)
                # new stone
                self.new_stone_p1()

    # ----------------------------------------------------------------
    # Player 2 Moves
    # ----------------------------------------------------------------
    def move_p2(self, delta_x):
        if not self.gameover_p2 and not self.paused:
            new_x = self.stone2_x + delta_x
            if new_x < 0:
                new_x = 0
            if new_x > config['cols'] - len(self.stone2[0]):
                new_x = config['cols'] - len(self.stone2[0])
            if not check_collision(self.board2, self.stone2, (new_x, self.stone2_y)):
                self.stone2_x = new_x

    def rotate_p2(self):
        if not self.gameover_p2 and not self.paused:
            new_stone = rotate_clockwise(self.stone2)
            if not check_collision(self.board2, new_stone, (self.stone2_x, self.stone2_y)):
                self.stone2 = new_stone

    def drop_p2(self):
        if not self.gameover_p2 and not self.paused:
            self.stone2_y += 1
            if check_collision(self.board2, self.stone2, (self.stone2_x, self.stone2_y)):
                self.stone2_y -= 1
                self.board2 = join_matrices(self.board2, self.stone2, (self.stone2_x, self.stone2_y))
                lines_cleared = 0
                while True:
                    for i, row in enumerate(self.board2):
                        if 0 not in row:
                            self.board2 = remove_row(self.board2, i)
                            lines_cleared += 1
                            break
                    else:
                        break

                if lines_cleared > 0:
                    if lines_cleared == 4:
                        garbage = 4
                        if self.b2b_p2:
                            garbage += 1
                        self.b2b_p2 = True
                    else:
                        garbage = lines_cleared - 1
                        self.b2b_p2 = False
                    self.board1 = add_garbage(self.board1, garbage)

                self.new_stone_p2()

    # ----------------------------------------------------------------
    # Misc
    # ----------------------------------------------------------------
    def toggle_pause(self):
        self.paused = not self.paused

    def quit(self):
        self.cap.release()
        cv2.destroyAllWindows()
        pygame.quit()
        sys.exit()

    # ----------------------------------------------------------------
    # The main game loop
    # ----------------------------------------------------------------
    def run(self):
        clock = pygame.time.Clock()

        while True:
            # 1) Grab a frame from the camera, run Mediapipe
            ret, frame = self.cap.read()
            if not ret:
                print("Camera read error!")
                self.quit()
            
            # Process with Mediapipe
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.hands_detector.process(image_rgb)

            # If we see hands, figure out if they're on the left or right half
            if results.multi_hand_landmarks:
                for hand_landmarks in results.multi_hand_landmarks:
                    # Draw the landmarks on the debug frame
                    self.mp_drawing.draw_landmarks(frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)

                    # Extract a few points for “gesture detection”
                    thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
                    index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    middle_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                    ring_tip   = hand_landmarks.landmark[self.mp_hands.HandLandmark.RING_FINGER_TIP]
                    pinky_tip  = hand_landmarks.landmark[self.mp_hands.HandLandmark.PINKY_TIP]

                    # Approx “hand center” by averaging tip x coords:
                    hand_center_x = (
                        thumb_tip.x + index_tip.x + middle_tip.x +
                        ring_tip.x + pinky_tip.x
                    ) / 5.0

                    # Example gestures
                    is_hand_closed = (
                        index_tip.y > thumb_tip.y and
                        middle_tip.y > thumb_tip.y and
                        ring_tip.y > thumb_tip.y and
                        pinky_tip.y > thumb_tip.y
                    )
                    is_pointing = (
                        index_tip.y < thumb_tip.y and 
                        middle_tip.y > index_tip.y and  
                        ring_tip.y > index_tip.y and
                        pinky_tip.y > index_tip.y
                    )

                    # Decide which player: left half <0.5 => P1, else => P2
                    if hand_center_x < 0.5:
                        # Player 1 logic
                        if is_pointing and not self.p1_is_pointing:
                            # Equivalent to pressing W => rotate
                            self.rotate_p1()
                            self.p1_is_pointing = True
                        elif is_hand_closed:
                            # Equivalent to pressing S => drop
                            self.drop_p1()
                        else:
                            # Move left or right?
                            if hand_center_x < 0.3:
                                # Move left => 'a'
                                self.move_p1(-1)
                                time.sleep(0.1)
                            elif hand_center_x > 0.35 and hand_center_x < 0.5:
                                # Move right => 'd'
                                self.move_p1(+1)
                                time.sleep(0.1)
                        # Reset pointing if not pointing
                        if not is_pointing:
                            self.p1_is_pointing = False

                    else:
                        # Player 2 logic
                        if is_pointing and not self.p2_is_pointing:
                            # 'UP' => rotate
                            self.rotate_p2()
                            self.p2_is_pointing = True
                        elif is_hand_closed:
                            # 'DOWN' => drop
                            self.drop_p2()
                        else:
                            # Move left or right?
                            # But for P2, "left" = K_LEFT => move_p2(-1), "right" = K_RIGHT => move_p2(+1)
                            if hand_center_x < 0.7:
                                # Move left
                                self.move_p2(-1)
                                time.sleep(0.1)
                            elif hand_center_x > 0.75:
                                # Move right
                                self.move_p2(+1)
                                time.sleep(0.1)
                        # Reset pointing
                        if not is_pointing:
                            self.p2_is_pointing = False

            # Show CV debug window
            cv2.imshow("Hand Gestures", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.quit()

            # 2) Handle pygame events (like ESC key, pause, etc.)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.quit()
                    if event.key == pygame.K_p:
                        self.toggle_pause()

                elif event.type == pygame.USEREVENT + 1:
                    # Automatic drop
                    if not self.paused:
                        if not self.gameover_p1:
                            self.drop_p1()
                        if not self.gameover_p2:
                            self.drop_p2()

            # 3) Draw the Tetris boards
            self.screen.fill((0,0,0))

            # Player 1 area
            self.draw_matrix(self.board1, offset=(0,0))
            if not self.gameover_p1:
                self.draw_matrix(self.stone1, offset=(self.stone1_x, self.stone1_y))
            else:
                self.center_msg("P1 Game Over",
                                offset_x=config['cell_size']*config['cols']//2, 
                                offset_y=self.screen_height//2)

            # Player 2 area
            offset_x_2 = config['cols'] + 2
            self.draw_matrix(self.board2, offset=(offset_x_2, 0))
            if not self.gameover_p2:
                self.draw_matrix(self.stone2, offset=(self.stone2_x + offset_x_2, self.stone2_y))
            else:
                center_x_2 = (offset_x_2*config['cell_size'] + config['cell_size']*config['cols']//2)
                self.center_msg("P2 Game Over", center_x_2, self.screen_height//2)

            # Pause overlay
            if self.paused:
                self.center_msg("Paused",
                                offset_x=self.screen_width//2,
                                offset_y=self.screen_height//2)

            pygame.display.update()
            clock.tick(config['maxfps'])

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
if __name__ == "__main__":
    game = Tetris2P()
    game.run()