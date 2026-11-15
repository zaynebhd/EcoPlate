-- EcoPlate : la base utilisateur reste vide; les recettes de la plateforme sont préchargées.
SET NAMES utf8mb4;
CREATE DATABASE IF NOT EXISTS ecoplate_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ecoplate_db;

-- Comptes et profils des organisations.
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  email         VARCHAR(254) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          ENUM('individual', 'organization') NOT NULL,
  created_at    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS organizations (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  user_id           INT NOT NULL UNIQUE,
  name              VARCHAR(150) NOT NULL,
  organization_type ENUM('association', 'hotel', 'restaurant') NOT NULL,
  address           VARCHAR(255) NOT NULL,
  phone             VARCHAR(30) NOT NULL,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS announcements (
  id                 INT AUTO_INCREMENT PRIMARY KEY,
  organization_id    INT NOT NULL,
  food_name          VARCHAR(100) NOT NULL,
  quantity_total     INT NOT NULL,
  quantity_available INT NOT NULL,
  normal_price       DECIMAL(10,2) NOT NULL,
  reduced_price      DECIMAL(10,2) NOT NULL,
  deadline           DATE NOT NULL,
  description        TEXT NOT NULL,
  created_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_announcements_org_created (organization_id, created_at),
  INDEX idx_announcements_offers (deadline, quantity_available),
  FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS reservations (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  announcement_id INT NOT NULL,
  user_id         INT NOT NULL,
  quantity        INT NOT NULL,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_reservations_user (user_id, created_at),
  FOREIGN KEY (announcement_id) REFERENCES announcements(id) ON DELETE CASCADE,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS aliment (
  id_aliment      INT AUTO_INCREMENT PRIMARY KEY,
  user_id         INT NULL,
  nom             VARCHAR(100) NOT NULL,
  quantite        INT NOT NULL,
  date_peremption DATE,
  statut          VARCHAR(20) NOT NULL DEFAULT 'available',  -- available | consumed | wasted
  date_statut     DATE NULL,                                 -- date du passage à consumed / wasted
  INDEX idx_aliment_user_status (user_id, statut, date_peremption),
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS recette (
  id_recette  INT AUTO_INCREMENT PRIMARY KEY,
  nom         VARCHAR(100) NOT NULL,
  description TEXT
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS ingredient (
  id_ingredient INT AUTO_INCREMENT PRIMARY KEY,
  id_recette    INT NOT NULL,
  nom           VARCHAR(100) NOT NULL,
  FOREIGN KEY (id_recette) REFERENCES recette(id_recette) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS recipes (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  name        VARCHAR(150) NOT NULL UNIQUE,
  description TEXT NOT NULL
) CHARACTER SET utf8mb4;

CREATE TABLE IF NOT EXISTS recipe_ingredients (
  id              INT AUTO_INCREMENT PRIMARY KEY,
  recipe_id       INT NOT NULL,
  ingredient_name VARCHAR(100) NOT NULL,
  UNIQUE KEY uq_recipe_ingredient (recipe_id, ingredient_name),
  FOREIGN KEY (recipe_id) REFERENCES recipes(id) ON DELETE CASCADE
) CHARACTER SET utf8mb4;

-- Recettes de base de la plateforme, ajoutées de façon idempotente.
INSERT IGNORE INTO recipes (id, name, description) VALUES
  (1, 'Omelette aux tomates', 'Une omelette simple avec des tomates fondantes et de l’oignon.'),
  (2, 'Pâtes à la tomate', 'Des pâtes accompagnées d’une sauce rapide à la tomate et à l’ail.'),
  (3, 'Salade croquante', 'Une salade fraîche à base de légumes de saison.'),
  (4, 'Soupe de légumes', 'Une soupe réconfortante de carottes, pommes de terre et oignons.'),
  (5, 'Riz sauté aux légumes', 'Du riz sauté avec des œufs et des légumes.'),
  (6, 'Gratin de pommes de terre', 'Des pommes de terre gratinées avec du fromage et de la crème.'),
  (7, 'Tartines tomate-fromage', 'Du pain grillé garni de tomate et de fromage.'),
  (8, 'Crêpes maison', 'Une pâte à crêpes classique avec des ingrédients du placard.'),
  (9, 'Salade de pâtes', 'Une salade froide de pâtes, légumes et fromage.'),
  (10, 'Poulet aux légumes', 'Du poulet accompagné de légumes cuits au four.'),
  (11, 'Curry de lentilles', 'Des lentilles mijotées avec tomate, oignon et riz.'),
  (12, 'Sandwich au thon', 'Un sandwich frais au thon et aux crudités.'),
  (13, 'Galettes de carottes', 'Des galettes dorées à base de carottes et d’œuf.'),
  (14, 'Smoothie banane', 'Un smoothie rapide à la banane, au lait et au yaourt.'),
  (15, 'Ratatouille simple', 'Des légumes mijotés ensemble avec de la tomate.'),
  (16, 'Poisson au citron et riz', 'Du poisson servi avec du riz et une touche de citron.'),
  (17, 'Pommes au four', 'Des pommes doucement cuites avec du sucre et de la cannelle.'),
  (18, 'Quiche fromage-oignon', 'Une quiche familiale au fromage et à l’oignon.');

INSERT IGNORE INTO recipe_ingredients (recipe_id, ingredient_name) VALUES
  (1, 'œuf'), (1, 'tomate'), (1, 'oignon'),
  (2, 'pâtes'), (2, 'tomate'), (2, 'ail'),
  (3, 'laitue'), (3, 'tomate'), (3, 'concombre'), (3, 'carotte'),
  (4, 'carotte'), (4, 'pommes de terre'), (4, 'oignon'), (4, 'bouillon'),
  (5, 'riz'), (5, 'œuf'), (5, 'carotte'), (5, 'oignon'),
  (6, 'pommes de terre'), (6, 'fromage'), (6, 'crème'),
  (7, 'pain'), (7, 'tomate'), (7, 'fromage'),
  (8, 'farine'), (8, 'lait'), (8, 'œuf'),
  (9, 'pâtes'), (9, 'tomate'), (9, 'concombre'), (9, 'fromage'),
  (10, 'poulet'), (10, 'carotte'), (10, 'pommes de terre'), (10, 'oignon'),
  (11, 'lentilles'), (11, 'tomate'), (11, 'oignon'), (11, 'riz'),
  (12, 'pain'), (12, 'thon'), (12, 'tomate'), (12, 'laitue'),
  (13, 'carotte'), (13, 'œuf'), (13, 'farine'),
  (14, 'banane'), (14, 'lait'), (14, 'yaourt'),
  (15, 'courgette'), (15, 'aubergine'), (15, 'tomate'), (15, 'oignon'),
  (16, 'poisson'), (16, 'citron'), (16, 'riz'),
  (17, 'pomme'), (17, 'sucre'), (17, 'cannelle'),
  (18, 'œuf'), (18, 'lait'), (18, 'fromage'), (18, 'oignon');
