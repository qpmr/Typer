import time


class Statistics:
    def __init__(self):
        self.errors = 0
        self.speed_cpm = 0
        self.speed_wpm = 0
        self.time_ms = None
        self.word_cnt = 0
        self.symbol_cnt = 0

    def upd_err(self):
        self.errors += 1

    def upd_speed(self):
        self.symbol_cnt += 1

        if not self.time_ms:
            self.time_ms = time.time()
        else:
            if self.word_cnt == 0:
                return
            elapsed_time_ms = time.time() - self.time_ms
            if elapsed_time_ms:
                self.speed_cpm = int(self.symbol_cnt / elapsed_time_ms * 60)
                self.speed_wpm = self.speed_cpm / 5

    def reset(self):
        self.errors = 0
        self.time_ms = 0
        self.speed_cpm = self.speed_wpm = 0
        self.word_cnt = self.symbol_cnt = 0

    def one_word_typed(self):
        self.word_cnt += 1

    def __iter__(self):
        return iter((self.errors, self.speed_wpm))
