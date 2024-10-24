class Hangman:
    def __init__(self, word):
        self.word = word
        self.lives = 6
        self.guessed = []
        self.incorrect_guesses = []

    def guess(self, letter):
        if letter in self.guessed or letter in self.incorrect_guesses:
            return f"La letra '{letter}' ya fue utilizada."
        elif letter in self.word:
            self.guessed.append(letter)
            return "¡Correcto!"
        else:
            self.incorrect_guesses.append(letter)
            self.lives -= 1
            return "Incorrecto."

    def get_masked_word(self):
        return ' '.join([letter if letter in self.guessed else '_' for letter in self.word])

    def is_game_over(self):
        return self.lives <= 0 or self.get_masked_word().replace(' ', '') == self.word