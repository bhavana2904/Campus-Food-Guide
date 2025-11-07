CREATE DATABASE IF NOT EXISTS food;
USE food;

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    student_id VARCHAR(20),
    profile_image_url VARCHAR(255) DEFAULT 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT1pEdTSj3BgYH3tqCYYV9nSOa8kPt7Jn40HA&s',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

select *from users;
select *from FoodReviews;

CREATE TABLE canteens (
    canteen_id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    image_url VARCHAR(255),  -- Optional: for displaying canteen image
    location VARCHAR(100),   -- Optional: building/floor/campus zone
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE FoodReviews (
    ReviewID INT PRIMARY KEY AUTO_INCREMENT,
    FoodName VARCHAR(255) NOT NULL,
    Price DECIMAL(10, 2) NOT NULL,
    Rating INT NOT NULL CHECK (Rating BETWEEN 1 AND 5),
    SpiceLevel INT CHECK (SpiceLevel BETWEEN 0 AND 5),
    Review TEXT,
    ImagePaths TEXT,  -- JSON or comma-separated paths
    SubmissionDate DATETIME DEFAULT CURRENT_TIMESTAMP,

    UserID INT,
    CanteenID INT,
    FOREIGN KEY (UserID) REFERENCES users(user_id),
    FOREIGN KEY (CanteenID) REFERENCES canteens(canteen_id)
);

select *from FoodReviews;

CREATE TABLE Upvotes (
    UpvoteID INT PRIMARY KEY AUTO_INCREMENT,
    UserID INT NOT NULL,
    ReviewID INT NOT NULL,
    UpvoteDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES users(user_id),
    FOREIGN KEY (ReviewID) REFERENCES FoodReviews(ReviewID),
    UNIQUE (UserID, ReviewID)  -- Prevent duplicate upvotes
);

CREATE TABLE Favorites (
    FavoriteID INT PRIMARY KEY AUTO_INCREMENT,
    UserID INT NOT NULL,
    ReviewID INT NOT NULL,
    FavoriteDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES users(user_id),
    FOREIGN KEY (ReviewID) REFERENCES FoodReviews(ReviewID),
    UNIQUE (UserID, ReviewID)  -- Prevent duplicate favorites
);

CREATE TABLE Comments (
    CommentID INT PRIMARY KEY AUTO_INCREMENT,
    ReviewID INT NOT NULL,
    UserID INT NOT NULL,
    CommentText TEXT NOT NULL,
    CommentDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (ReviewID) REFERENCES FoodReviews(ReviewID) ON DELETE CASCADE,
    FOREIGN KEY (UserID) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE UserActivity (
    ActivityID INT PRIMARY KEY AUTO_INCREMENT,
    UserID INT NOT NULL,
    PostID INT,
    ActivityType VARCHAR(50) NOT NULL,  -- e.g. 'upvote', 'favorite', 'comment', 'review'
    ActivityTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (UserID) REFERENCES users(user_id),
    FOREIGN KEY (PostID) REFERENCES FoodReviews(ReviewID)
);



INSERT INTO canteens (name, description, image_url, location)
VALUES
  ('Pixel Canteen', 'Affordable and delicious local cuisine', '/templates/public/PIXEL.png', 'Ground Floor'),
  ('4th Floor Cafeteria', 'Street food paradise with authentic tastes', '/templates/public/4TH_FLOOR.png', '4th Floor'),
  ('5th Floor Cafeteria', 'Quick bites and beverages for study sessions', '/templates/public/5TH_FLOOR.png', '5th Floor'),
  ('MRD Canteen', 'Traditional Indian cuisine with modern twists', '/templates/public/mrd.png', 'MRD Building');
  
  select *from canteens;
  
select *from Favorites;
select *from Upvotes;
select *from Comments;
select * from UserActivity;

show tables;

-- Triggers
DELIMITER $$
CREATE TRIGGER fav_before_insert_prevent_own
BEFORE INSERT ON Favorites
FOR EACH ROW
BEGIN
  DECLARE owner_id INT;
  SELECT UserID INTO owner_id FROM FoodReviews WHERE ReviewID = NEW.ReviewID;
  IF owner_id IS NOT NULL AND owner_id = NEW.UserID THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot favorite your own review';
  END IF;
END$$
DELIMITER ;


DELIMITER $$
CREATE TRIGGER trg_upvotes_before_insert_prevent_own
BEFORE INSERT ON Upvotes
FOR EACH ROW
BEGIN
  DECLARE owner_id INT;
  SELECT UserID INTO owner_id FROM FoodReviews WHERE ReviewID = NEW.ReviewID;
  IF owner_id IS NOT NULL AND owner_id = NEW.UserID THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Cannot upvote your own review';
  END IF;
END$$
DELIMITER ;

DELIMITER //

CREATE TRIGGER prevent_negative_price
BEFORE INSERT ON FoodReviews
FOR EACH ROW
BEGIN
    IF NEW.Price < 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Price cannot be negative';
    END IF;
END;
//

DELIMITER ;

-- //Get reviews with author names
SELECT r.FoodName, r.Review, u.username
FROM FoodReviews r
JOIN users u ON r.UserID = u.user_id;

-- Get total upvotes per review
SELECT ReviewID, COUNT(*) AS total_upvotes
FROM Upvotes
GROUP BY ReviewID;

-- Function to compute average rating for a food item
DELIMITER //

CREATE FUNCTION GetAverageRating(food_name VARCHAR(255))
RETURNS DECIMAL(5,2)
DETERMINISTIC
BEGIN
    DECLARE avg_rating DECIMAL(5,2);
    SELECT AVG(Rating) INTO avg_rating
    FROM FoodReviews
    WHERE FoodName = food_name;
    RETURN avg_rating;
END;
//

DELIMITER ;
SELECT GetAverageRating('Brownie');


-- Insert a new review into FoodReviews
-- Log the action into UserActivity

DELIMITER //

CREATE PROCEDURE AddReviewWithActivity (
    IN p_food_name VARCHAR(255),
    IN p_price DECIMAL(10,2),
    IN p_rating INT,
    IN p_spice_level INT,
    IN p_review TEXT,
    IN p_image_paths TEXT,
    IN p_user_id INT,
    IN p_canteen_id INT
)
BEGIN
    DECLARE new_review_id INT;

    INSERT INTO FoodReviews (
        FoodName, Price, Rating, SpiceLevel, Review, ImagePaths, UserID, CanteenID
    ) VALUES (
        p_food_name, p_price, p_rating, p_spice_level, p_review, p_image_paths, p_user_id, p_canteen_id
    );

    SET new_review_id = LAST_INSERT_ID();

    INSERT INTO UserActivity (
        UserID, ReviewID, ActivityType
    ) VALUES (
        p_user_id, new_review_id, 'review'
    );
END;
//

DELIMITER ;

CALL AddReviewWithActivity(
    'Brownie', 50.00, 5, 2, 'So good rich yummy MUST TRY!!!!',
    '["/static/uploads/brownie.jpg"]', 3, 1
);
