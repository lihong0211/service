ALTER TABLE english_new.daily_expressions
    ADD COLUMN audio_url VARCHAR(255) NULL COMMENT '日常表达发音音频地址' AFTER meaning;
