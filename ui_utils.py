import cv2
import numpy as np

def draw_button(img, pos1, pos2, text, color_bg=(251, 250, 247), color_text=(0, 0, 0)):
    cv2.rectangle(img, pos1, pos2, color_bg, -1)
    font = cv2.FONT_HERSHEY_SIMPLEX
    textsize = cv2.getTextSize(text, font, 1, 2)[0]
    text_x = (pos1[0] + pos2[0] - textsize[0]) // 2
    text_y = (pos1[1] + pos2[1] + textsize[1]) // 2
    cv2.putText(img, text, (text_x, text_y), font, 1, color_text, 2)

def draw_question_interface(canvas, question, can_answer=True):
    canvas[:] = (251, 250, 247)
    h, w = canvas.shape[:2]
    margin = 20
    line_height = 40

    # Question text
    y = margin + line_height
    cv2.putText(canvas, question['question_text'], (margin, y), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    y += line_height * 2

    # Answers
    box_w = w - 2 * margin
    box_h = 50
    colors = [(100, 255, 100) if can_answer else (70, 70, 70)] * 4

    answer_boxes = []
    for i, ans in enumerate(question['answers']):
        top_left = (margin, y + i * (box_h + 10))
        bottom_right = (margin + box_w, y + i * (box_h + 10) + box_h)
        color = (251, 250, 247) if can_answer else (100, 100, 100) # (100, 100, 100) is a darker grey for when can_answer is False
        cv2.rectangle(canvas, top_left, bottom_right, color, -1)
        cv2.putText(canvas, f"{i+1}. {ans}", (top_left[0] + 10, top_left[1] + 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        answer_boxes.append((top_left[0], top_left[1], bottom_right[0], bottom_right[1]))
    return answer_boxes

def draw_main_menu(img):
    img[:] = (251, 250, 247)
    draw_button(img, (100, 100), (250, 180), "Student", (0, 255, 0))
    draw_button(img, (350, 100), (500, 180), "Teacher", (255, 0, 0))

def draw_text_input_box(img, text, pos=(50, 200), width=400, height=50):
    cv2.rectangle(img, pos, (pos[0] + width, pos[1] + height), (255, 255, 255), 2)
    cv2.putText(img, text, (pos[0] + 10, pos[1] + 35), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
