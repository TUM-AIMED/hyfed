"""
    Utility functions to create different widgets

    Copyright 2021 Reza NasiriGerdeh. All Rights Reserved.

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.
"""


import tkinter as tk
from tkinter import filedialog


def add_labels(widget, left_label_text, right_label_text, label2_width=25, label_font=('times', 11),
               padx=10, pady=10, sticky="", increment_row_number=True):
    """ Create two labels (left label and right label) in a row """

    left_label = tk.Label(widget, text=left_label_text)
    left_label.config(font=label_font)
    left_label.grid(row=widget.row_number, column=0, padx=padx, pady=pady, sticky=sticky)

    right_label = tk.Label(widget, text=right_label_text)
    right_label.config(width=label2_width, font=label_font)
    right_label.grid(row=widget.row_number, column=1, padx=padx, pady=pady, sticky=sticky)

    if increment_row_number:
        widget.row_number += 1

    return right_label


def add_label_and_textbox(widget, label_text, label_font=('times', 11), padx=10, pady=10, sticky="",
                          value="", status="normal", increment_row_number=True):
    """ Create a label in the left side and a textbox in right side of a row """

    label = tk.Label(widget, text=label_text)
    label.config(font=label_font)
    label.grid(row=widget.row_number, column=0, padx=padx, pady=pady, sticky=sticky)

    text_entry = tk.Entry(widget, width=widget.textbox_width)

    text_entry.config(font=label_font)
    if value:
        text_entry.insert(tk.END, value)
        text_entry.config(state=status)
    text_entry.grid(row=widget.row_number, column=1, padx=padx, pady=pady, sticky=sticky)

    if increment_row_number:
        widget.row_number += 1

    return text_entry


def add_label_and_password_box(widget, label_text, label_font=('times', 11), padx=10, pady=10, sticky=""):
    """ Create a label in the left side and a password box in the right side of a row """

    label = tk.Label(widget, text=label_text)
    label.config(font=label_font)
    label.grid(row=widget.row_number, column=0, padx=padx, pady=pady, sticky=sticky)

    password_entry = tk.Entry(widget, show='*', width=widget.textbox_width)
    password_entry.config(font=label_font)
    password_entry.grid(row=widget.row_number, column=1, padx=padx, pady=pady, sticky=sticky)

    widget.row_number += 1

    return password_entry


def add_option_menu(widget, label_text, choices, label_font=('times', 11), padx=10, pady=10, sticky=tk.EW):
    """ Create a label in the left side and an option menu in the right side of a row """

    label = tk.Label(widget, text=label_text)
    label.config(font=label_font)
    label.grid(row=widget.row_number, column=0, padx=padx, pady=pady)

    option_value = tk.StringVar(widget)
    option_value.set(choices[0])

    option_menu = tk.OptionMenu(widget, option_value, *choices)
    option_menu.config(font=label_font)
    option_menu.grid(row=widget.row_number, column=1, padx=padx, pady=pady, sticky=sticky)

    widget.row_number += 1

    return option_value


def add_button(widget, button_label, column_number, on_click_function, increment_row_number=False, label_font=('times', 11),
               padx=10, pady=10, sticky=tk.W):
    """ Add a button to a specified column of a row """

    button = tk.Button(widget, text=button_label, command=on_click_function)
    button.config(font=label_font)
    button.grid(row=widget.row_number, column=column_number, padx=padx, pady=pady, sticky=sticky)

    if increment_row_number:
        widget.row_number += 1

    return button


def select_file_path(text_box_entry, is_directory=False, file_types=[]):
    """ Open a directory/file dialog and return the path of the directory/file selected by the user """

    if is_directory:
        user_selected_path = filedialog.askdirectory()
    else:
        user_selected_path = filedialog.askopenfilename(filetypes=file_types)

    text_box_entry.delete(0, tk.END)
    text_box_entry.insert(0, user_selected_path)

    return user_selected_path


def create_log_widget(title, textbox_height=20, textbox_width=100, scrollbar_width=30, font=('Times', 12)):
    """ Open a log widget to show the client log messages """

    log_widget = tk.Tk()

    log_widget.title(title)

    log_textbox = tk.Text(log_widget, height=textbox_height, width=textbox_width)
    log_scrollbar = tk.Scrollbar(log_widget, width=scrollbar_width)

    log_textbox.config(yscrollcommand=log_scrollbar.set, font=font)
    log_scrollbar.config(command=log_textbox.yview)

    log_textbox.grid(row=0, column=0)
    log_scrollbar.grid(row=0, column=1, sticky=tk.N + tk.S)

    return log_widget, log_textbox
