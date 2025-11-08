# Campus Food Guide  
### UE23CS351A – Database Management System Mini Project  

## Project Overview
The **Campus Food Guide** is a web-based application designed to help PES University students, faculty, and staff explore food options available across campus canteens.  
It enables users to read authentic peer reviews, view prices and ratings, and make informed dining choices — all within a centralized, easy-to-use platform.

---

## Objective
To design and develop a **database-driven food discovery and review system** that provides real-time information about food items, enables community feedback, and supports canteen operators with data-driven insights.

---

## Team Details

| Name | USN | 
|------|------|
| **Ankana Mandal** | PES2UG23CS076 | 
| **Bhavana** | PES2UG23CS905 |

---

## Features

- **User Registration & Login** – Secure authentication using university credentials.  
- **Browse Food Items** – Explore menus from all four campus canteens (Pixel, 4th Floor, 5th Floor, MRD).  
- **Ratings & Reviews** – Students can rate, review, and upload photos for food items.  
- **Favorites & Upvotes** – Users can favorite items or upvote helpful reviews (with trigger-based validation).  
- **Comments System** – Interact with peers through review comments.  
- **Canteen Dashboard** – Canteen operators manage items, prices, and availability.  
- **Personalized Recommendations** – Suggested items based on user preferences and past reviews.  
- **Admin Panel** – Manages users, reviews, and maintains database integrity.  
- **Analytics & Reports** – Aggregated data for canteen popularity and performance.  

---

## 🗄️ Database Design

**Database Name:** `food`

### **Main Tables**
- `users` – Stores user credentials and profile information.  
- `canteens` – Details of each canteen on campus.  
- `FoodReviews` – Stores reviews, prices, ratings, and photos.  
- `Favorites`, `Upvotes`, `Comments` – Handles user interactions.  
- `UserActivity` – Logs user actions for analytics.  

### **Relationships**
- One-to-Many: `canteens → FoodReviews`  
- One-to-Many: `users → FoodReviews`  
- Many-to-Many: Implemented via `Favorites` and `Upvotes`

---

## Technologies Used

| Category | Tools / Languages |
|-----------|-------------------|
| **Frontend** | HTML5, CSS3, JavaScript |
| **Backend** | Python (Flask Framework) |
| **Database** | MySQL |
| **IDE / Tools** | VS Code, MySQL Workbench |
| **ER Diagram** | draw.io |
| **Version Control** | Git, GitHub |

---

## SQL Components

### **DDL Commands**
Defined schema for all tables including `users`, `canteens`, `FoodReviews`, `Favorites`, `Upvotes`, `Comments`, and `UserActivity`.

### **Triggers**
- Prevent negative prices in food entries  
- Prevent users from upvoting/favoriting their own reviews  

### **Functions**
- `GetAverageRating(food_name)` → Returns average rating of a food item  

### **Stored Procedure**
- `AddReviewWithActivity()` → Inserts a new review and logs it in `UserActivity`  

---

## CRUD Operations
| Operation | Example |
|------------|----------|
| **Create** | Add new review via web form or `INSERT INTO FoodReviews(...)` |
| **Read** | Display all reviews with `SELECT` queries |
| **Update** | Modify item price or availability |
| **Delete** | Remove outdated reviews or comments |

---

## Sample Queries

```sql
-- Average rating per canteen
SELECT c.name AS canteen_name, AVG(r.Rating) AS avg_rating
FROM FoodReviews r
JOIN canteens c ON r.CanteenID = c.canteen_id
GROUP BY c.canteen_id;

-- Most reviewed items
SELECT FoodName, COUNT(*) AS total_reviews
FROM FoodReviews
GROUP BY FoodName
ORDER BY total_reviews DESC;
