-- INSERIMENTO DEI CORSI DI LAUREA TRIENNALE (Bachelor's Degree)
--

INSERT INTO degree (id, name, type, category) VALUES
('L33', 'Economia e Commercio', 'Bachelor''s Degree', 'Economics'),
('L18', 'Economia Aziendale e Digital Business', 'Bachelor''s Degree', 'Economics'),
('L7', 'Ingegneria Civile e Ambientale', 'Bachelor''s Degree', 'Enginering'),
('L8', 'Ingegneria Informatica, Elettronica e Videogame', 'Bachelor''s Degree', 'Enginering'),
('L9', 'Ingegneria Meccanica e per la Sostenibilità', 'Bachelor''s Degree', 'Enginering'),
('L23', 'Ingegneria Edile', 'Bachelor''s Degree', 'Enginering'),
('L9-L8', 'Ingegneria Gestionale (Interclasse)', 'Bachelor''s Degree', 'Enginering'),
('L13', 'Scienze Biologiche', 'Bachelor''s Degree', 'Science'),
('L32', 'Scienze Ambientali e Protezione Civile', 'Bachelor''s Degree', 'Science'),
('L22', 'Scienze Motorie per la Salute', 'Bachelor''s Degree', 'Science'),
('L25', 'Scienze Forestali e Ambientali / Sistemi Agricoli', 'Bachelor''s Degree', 'Agriculture'),
('L26', 'Scienze e Tecnologie Alimentari', 'Bachelor''s Degree', 'Agriculture'),
('LSNT1', 'Infermieristica e Ostetricia', 'Bachelor''s Degree', 'Medicine'),
('LSNT2', 'Fisioterapia e Logopedia', 'Bachelor''s Degree', 'Medicine'),
('LSNT3', 'Dietistica e Tecniche Sanitarie (varie)', 'Bachelor''s Degree', 'Medicine'),
('LSNT4', 'Tecniche della Prevenzione nell''Ambiente e nei Luoghi di Lavoro', 'Bachelor''s Degree', 'Medicine');

--
-- INSERIMENTO DEI CORSI DI LAUREA MAGISTRALE (Master's Degree)
--

INSERT INTO degree (id, name, type, category) VALUES
('LM77', 'Economia e Management / Management della Sostenibilità', 'Master''s Degree', 'Economics'),
('LM56', 'International Economics and Commerce / Data Science', 'Master''s Degree', 'Economics'),
('LM16', 'Scienze Economiche e Finanziarie', 'Master''s Degree', 'Economics'),
('LM21', 'Biomedical Engineering', 'Master''s Degree', 'Enginering'),
('LM23', 'Ingegneria Civile', 'Master''s Degree', 'Enginering'),
('LM24', 'Ingegneria Edile', 'Master''s Degree', 'Enginering'),
('LM29', 'Ingegneria Elettronica', 'Master''s Degree', 'Enginering'),
('LM30', 'Green Industrial Engineering', 'Master''s Degree', 'Enginering'),
('LM31', 'Ingegneria Gestionale', 'Master''s Degree', 'Enginering'),
('LM32', 'Ingegneria Informatica e dell''Automazione', 'Master''s Degree', 'Enginering'),
('LM33', 'Ingegneria Meccanica e Logistica', 'Master''s Degree', 'Enginering'),
('LM35', 'Environmental Engineering', 'Master''s Degree', 'Enginering'),
('LM6', 'Biologia Marina e Biologia Molecolare', 'Master''s Degree', 'Science'),
('LM75', 'Environmental Hazard and Disaster Risk Management', 'Master''s Degree', 'Science'),
('LM61', 'Scienze della Nutrizione e dell''Alimentazione', 'Master''s Degree', 'Science'),
('LM3', 'Paesaggio, Innovazione e Sostenibilità', 'Master''s Degree', 'Agriculture'),
('LM69', 'Scienze Agrarie e del Territorio', 'Master''s Degree', 'Agriculture'),
('LM70', 'Food and Beverage Innovation and Management', 'Master''s Degree', 'Agriculture'),
('LM73', 'Scienze e Tecnologie Forestali e Ambientali', 'Master''s Degree', 'Agriculture'),
('LMSN1', 'Scienze Infermieristiche ed Ostetriche', 'Master''s Degree', 'Medicine'),
('LMSN2', 'Scienze Riabilitative delle Professioni Sanitarie', 'Master''s Degree', 'Medicine');

--
-- INSERIMENTO DEI CORSI A CICLO UNICO (Single-Cycle Degree)
--

INSERT INTO degree (id, name, type, category) VALUES
('LM4CU', 'Ingegneria edile-architettura', 'Single-Cycle Degree', 'Enginering'),
('LM41', 'Medicina e Chirurgia / Medicine and Surgery', 'Single-Cycle Degree', 'Medicine'),
('LM46', 'Odontoiatria e Protesi Dentaria', 'Single-Cycle Degree', 'Medicine');