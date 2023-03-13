"""
Briefing: The code is an implementation of a WordNetwork class in Python that performs several NLP tasks including:
          > Text cleaning
          > Generation of n-grams
          > Word frequency analysis
          > Wordcloud visualization
          > Topic modeling
          > General text statistics

  $ pip install spacy
  $ python -m spacy download en_core_web_sm
  $ python -m spacy validate

  It starts by processing the input data and stopwords, then it calls several methods to perform each of the
  tasks mentioned above. The results of these tasks are then printed or visualized, including a graph
  representation of the co-occurrence matrix, the top n-grams, word frequency histogram, entropy of the text,
  etc.
"""

import os
import re
import tkinter as tk
import warnings
from collections import Counter, defaultdict
from math import log
from tkinter import filedialog

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import pyLDAvis.gensim
import spacy
from gensim.corpora import Dictionary
from gensim.models.ldamodel import LdaModel
from pandas import DataFrame
from PIL import ImageTk
from pyvis.network import Network
from scipy.stats import entropy
from wordcloud import WordCloud

warnings.filterwarnings("ignore", '.*the imp module.*')
warnings.filterwarnings("ignore", category=DeprecationWarning, module='wordcloud')
warnings.filterwarnings("ignore", category=FutureWarning, module='pyLDAvis')


class TextAnalysisGUI:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Text Analysis Results")
        self.window.geometry("800x600")

        # Create frame for input file selection
        self.input_frame = tk.Frame(self.window)
        self.input_frame.pack(side=tk.TOP, fill=tk.X)

        # Create input file label and browse button
        self.input_filename = ''
        self.input_file_label = tk.Label(self.input_frame, text='Input File: {}'.format(self.input_filename))
        self.input_file_label.pack(side=tk.LEFT, padx=5)
        self.input_browse_button = tk.Button(self.input_frame, text="Browse", command=self.browse_input_file)
        self.input_browse_button.pack(side=tk.LEFT, padx=5)

        # Create frame for stopword file selection
        self.stopword_frame = tk.Frame(self.window)
        self.stopword_frame.pack(side=tk.TOP, fill=tk.X)

        # Create stopword file label and browse button
        self.stopword_filename = ''
        self.stopword_file_label = tk.Label(self.stopword_frame,
                                            text='Stopword File: {}'.format(self.stopword_filename))
        self.stopword_file_label.pack(side=tk.LEFT, padx=5)
        self.stopword_browse_button = tk.Button(self.stopword_frame, text="Browse", command=self.browse_stopword_file)
        self.stopword_browse_button.pack(side=tk.LEFT, padx=5)

        # Create frame for options
        self.options_frame = tk.Frame(self.window)
        self.options_frame.pack(side=tk.TOP, fill=tk.X)

        # Create enable console prints checkbox
        self.enable_console_prints_var = tk.BooleanVar(value=False)
        self.enable_console_prints_checkbox = tk.Checkbutton(self.options_frame, text='Enable Console Prints',
                                                             variable=self.enable_console_prints_var)
        self.enable_console_prints_checkbox.pack(side=tk.LEFT, padx=5)

        # Create save graph checkbox
        self.save_graph_var = tk.BooleanVar(value=False)
        self.save_graph_checkbox = tk.Checkbutton(self.options_frame, text='Save Graph',
                                                  variable=self.save_graph_var)
        self.save_graph_checkbox.pack(side=tk.LEFT, padx=5)

        # Create save wordcloud checkbox
        self.save_wordcloud_var = tk.BooleanVar(value=False)
        self.save_wordcloud_checkbox = tk.Checkbutton(self.options_frame, text='Save Wordcloud',
                                                      variable=self.save_wordcloud_var)
        self.save_wordcloud_checkbox.pack(side=tk.LEFT, padx=5)

        # Create generate button
        self.generate_button = tk.Button(self.window, text="Generate", command=self.generate_analysis)
        self.generate_button.pack(side=tk.TOP, pady=10)

        # Create text widget to display results
        self.text_widget = tk.Text(self.window)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create canvas widget to display wordcloud
        self.canvas = tk.Canvas(self.window, bg="white", width=600, height=600)
        self.canvas.pack(side=tk.RIGHT)

        self.window.mainloop()

    def browse_input_file(self):
        input_path = tk.filedialog.askopenfilename(
            initialdir="/", title="Select file",
            filetypes=(("Text Files", "*.txt"), ("All Files", "*.*"))
        )
        self.input_filename = os.path.basename(input_path)
        self.input_file_label.config(text='Input File: {}'.format(self.input_filename))

    def browse_stopword_file(self):
        stopword_filename = tk.filedialog.askopenfilename(
            initialdir="/",
            title="Select file",
            filetypes=(("Text Files", "*.txt"), ("All Files", "*.*"))
        )
        self.stopword_filename = os.path.basename(stopword_filename)
        self.stopword_file_label.config(text='Stopword File: {}'.format(self.stopword_filename))

    def generate_analysis(self):
        self.text_widget.delete('1.0', tk.END)

        # print(f'input_filename: {self.input_filename}\n'
        #       f'stopword_filename: {self.stopword_filename}\n'
        #       f'enable_console_prints: {self.enable_console_prints_var.get()}\n'
        #       f'save_graph: {self.save_graph_var.get()}\n'
        #       f'save_wordcloud: {self.save_wordcloud_var.get()}\n')

        text_analysis = TextAnalysis(
            input_filename=self.input_filename,
            stopword_filename=self.stopword_filename,
            enable_console_prints=self.enable_console_prints_var.get(),
            tkinter_root=self.window,
            save_graph=self.save_graph_var.get(),
            save_wordcloud=self.save_wordcloud_var.get()
        )

        self.text_widget.insert(tk.END, f"\n---This is an analysis for: {self.input_filename}")
        self.text_widget.insert(tk.END, "\n\n---Most Frequent N-Grams---\n")
        self.text_widget.insert(tk.END, text_analysis.most_frequent_ngrams.to_string(index=False))

        self.text_widget.insert(tk.END, "\n\n---Top Communities---\n")
        for community in text_analysis.top_comm:
            self.text_widget.insert(tk.END, f"\nCommunity {community[0]}: {community[1]}")

        self.text_widget.insert(tk.END, "\n\n---Text Entropy---\n")
        self.text_widget.insert(tk.END, f"\n{text_analysis.text_entropy:.2f}")


class TextAnalysis:
    def __init__(self,
                 input_filename: str,
                 stopword_filename: str,
                 enable_console_prints: bool,
                 tkinter_root,
                 save_graph: bool,
                 save_wordcloud: bool):
        self.input_filename = input_filename
        self.input_filepath = 'Inputs/{}'.format(input_filename)
        self.stopword_filepath = 'Inputs/{}'.format(stopword_filename)
        self.console = enable_console_prints
        self.root = tkinter_root
        self.save_graph = save_graph
        self.save_wordcloud = save_wordcloud

        self.raw_words = []
        self.stop_words = []
        self.filtered_words = []
        self.vocabulary = set()
        self.ngrams = []
        self.top_comm = []
        self.text_entropy = None
        self.wordcloud_image = None
        self.wordcloud = None

        self.n_size = 2
        self.num_topics = 5
        self.word_window = 4
        self.num_similar = 10
        self.min_word_length = 2
        self.most_frequent_ngrams = None

        # updating the stopword list
        self.additional_stopwords = ['engineering', 'data', 'engineers', 'digital', 'today', 'use', 'used']

        self._read_input_data()
        self._visualize_adjacency_matrix()
        self._text_cleaning(self.raw_words)
        self._generate_ngrams()
        self._calculate_frequency()
        self._print_most_frequent_ngrams()
        self._generate_wordcloud()
        self._topic_modeling()
        self._calculate_entropy()
        if self.console:
            self._print_text_statistics()

    def _read_input_data(self) -> None:
        if self.console:
            print(f"\n---This is an analysis for: {self.input_filepath}")

        self.raw_words = read_input(file=self.input_filepath)
        self.stop_words = read_input(file=self.stopword_filepath)
        self.stop_words.extend(self.additional_stopwords)

    def _visualize_adjacency_matrix(self) -> None:
        adj_matrix = self._co_occurrence()
        # print (adj_matrix)

        G = nx.from_pandas_adjacency(adj_matrix)
        visual_graph = Network(
            height="500px",
            bgcolor="#222222",
            font_color="white"
        )
        visual_graph.from_nx(G)
        visual_graph.show_buttons(filter_=['physics'])
        if self.save_graph:
            visual_graph.save_graph(self.input_filename + '.html')

    def _text_cleaning(self, words) -> None:
        # Load spaCy model
        nlp = spacy.load("en_core_web_sm")

        # Combine all raw words into a single text string
        text = ' '.join(words)

        # Perform Named Entity Recognition (NER) on the text
        doc = nlp(text)

        # Define regular expression pattern for names
        name_pattern = re.compile(r"\b([A-Z][a-z]+\s)*[A-Z][a-z]+\b")

        # Remove all names from the text
        names = []
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                name = ent.text
                text = re.sub(name_pattern, "", text)
                names.append(name)

        # Split the modified text into individual words
        words = text.split()

        # Filter out stop words and non-alphabetic words
        filtered_words = [word.lower() for word in words if
                          word.lower() not in self.stop_words and word.isalpha() and len(word) > self.min_word_length]

        # Remove the names from the filtered words and vocabulary
        for name in names:
            name_words = name.split()
            for name_word in name_words:
                if name_word.lower() in filtered_words:
                    filtered_words.remove(name_word.lower())
                if name_word.lower() in self.vocabulary:
                    self.vocabulary.remove(name_word.lower())

        # Update the filtered words and vocabulary lists
        self.filtered_words = filtered_words
        self.vocabulary = set(filtered_words)

    def _generate_ngrams(self) -> None:
        self.ngrams = ['_'.join(self.filtered_words[i:i + self.n_size]) for i in
                       range(len(self.filtered_words) - self.n_size + 1)]

    def _calculate_frequency(self) -> None:
        self.top_comm = [ngram for ngram, count in Counter(self.ngrams).most_common(self.num_similar)]

    def _print_most_frequent_ngrams(self) -> None:
        self.most_frequent_ngrams = ["{}. {}".format(_id + 1, ngram) for _id, ngram in enumerate(self.top_comm)]
        if self.console:
            print('\nThe following are the top {} -grams:\n{}'.format(
                self.num_similar, '\n'.join(self.most_frequent_ngrams)))

    def _generate_wordcloud(self) -> None:
        all_words_string = ' '.join(self.filtered_words + self.top_comm)
        all_stopwords_string = set(' '.join(self.stop_words))

        # defining the wordcloud parameters
        self.wordcloud = WordCloud(background_color="white",
                                   max_words=2000,
                                   stopwords=all_stopwords_string)

        # generate words cloud
        self.wordcloud_generated = self.wordcloud.generate(all_words_string)
        self.wordcloud_image = ImageTk.PhotoImage(self.wordcloud_generated.to_image())

        if self.save_wordcloud:
            # store to file
            _file = 'Outputs/{}.{}'.format(self.input_filename.replace('.txt', ''), '.png')
            self.wordcloud.to_file(filename=_file)

        if self.console:
            plt.imshow(self.wordcloud)
            plt.axis('off')
            plt.show()

    def _topic_modeling(self) -> None:
        tokens = [x.split() for x in self.filtered_words]
        dictionary = Dictionary(tokens)
        corpus = [dictionary.doc2bow(text) for text in tokens]

        lda = LdaModel(corpus=corpus,
                       num_topics=self.num_topics,
                       id2word=dictionary)
        if self.console:
            print('\n the following are the top', self.num_topics, 'topics:')

            for i in range(0, len(lda.show_topics(self.num_topics))):
                print(lda.show_topics(self.num_topics)[i][1], '\n')

        lda_display = pyLDAvis.gensim.prepare(lda, corpus, dictionary, sort_topics=False)

        return pyLDAvis.display(lda_display)

    def _co_occurrence(self) -> DataFrame:
        d = defaultdict(int)
        vocab = set()
        for text in self.raw_words:
            text = text.lower().split()
            self._text_cleaning(text)
            for i in range(len(self.filtered_words)):
                token = self.filtered_words[i]
                vocab.add(token)
                next_token = self.filtered_words[i + 1: i + 1 + self.word_window]
                for t in next_token:
                    key = tuple(sorted([t, token]))
                    d[key] += 1

        vocab = sorted(vocab)
        df = pd.DataFrame(data=np.zeros((len(vocab), len(vocab)), dtype=np.int16),
                          index=vocab,
                          columns=vocab)

        for key, value in d.items():
            df.at[key[0], key[1]] = value
            df.at[key[1], key[0]] = value

        return df

    def _calculate_entropy(self) -> None:
        words_counter = Counter(self.filtered_words)
        word_freq_lst = list(words_counter.values())
        self.text_entropy = entropy(word_freq_lst, base=10)

    def _print_text_statistics(self) -> None:
        stats = {
            'total_words':   len(self.filtered_words),
            'unique_words':  len(self.vocabulary),
            'total_entropy': round(log(self.text_entropy, 10), 2)
        }

        message = '\nThe following are some basic statistics on the input text.' \
                  '\n\tTotal number of words: {total_words}' \
                  '\n\tTotal number of unique words: {unique_words}' \
                  '\n\tTotal entropy in the text: {total_entropy}'.format(**stats)

        print(message)


def read_input(file) -> list[str]:
    file_name = file if file.lower().endswith('.txt') else file + '.txt'

    try:
        with open(file=file_name, mode='r', encoding='utf8') as fr1:
            return [word.strip() for word in fr1 if word]
    except FileNotFoundError:
        print('Error reading the input data')


if __name__ == '__main__':
    try:
        gui = TextAnalysisGUI()
    except KeyboardInterrupt:
        print('Execution terminated by User')
    except Exception as ex1:
        print('Something went wrong during execution: {}'.format(ex1))
