-- MySQL dump 10.13  Distrib 8.0.43, for macos15 (arm64)
--
-- Host: mudb.clu5gyyjyzym.ap-south-1.rds.amazonaws.com    Database: mu_dev
-- ------------------------------------------------------
-- Server version	8.0.42

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
SET @MYSQLDUMP_TEMP_LOG_BIN = @@SESSION.SQL_LOG_BIN;
SET @@SESSION.SQL_LOG_BIN= 0;

--
-- GTID state at the beginning of the backup 
--

SET @@GLOBAL.GTID_PURGED=/*!80000 '+'*/ '';

--
-- Table structure for table `achievement`
--

DROP TABLE IF EXISTS `achievement`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `achievement` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `level_id` varchar(36) DEFAULT NULL,
  `description` varchar(300) NOT NULL,
  `icon` varchar(100) DEFAULT NULL,
  `has_vc` tinyint(1) NOT NULL DEFAULT '0',
  `tags` json NOT NULL,
  `type` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `template_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `fk_achievement_ref_updated_by` (`updated_by`),
  KEY `fk_achievement_ref_created_by` (`created_by`),
  KEY `fk_achievement_ref_level` (`level_id`),
  CONSTRAINT `fk_achievement_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_achievement_ref_level` FOREIGN KEY (`level_id`) REFERENCES `level` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_achievement_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=17 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_user`
--

DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_user_groups`
--

DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_user_user_permissions`
--

DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `channel`
--

DROP TABLE IF EXISTS `channel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `channel` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `discord_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `fk_channel_ref_updated_by` (`updated_by`),
  KEY `fk_channel_ref_created_by` (`created_by`),
  CONSTRAINT `fk_channel_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_channel_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `channel_backup`
--

DROP TABLE IF EXISTS `channel_backup`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `channel_backup` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `discord_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `circle_meet_attendees`
--

DROP TABLE IF EXISTS `circle_meet_attendees`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `circle_meet_attendees` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `meet_id` varchar(36) NOT NULL,
  `is_joined` tinyint(1) NOT NULL DEFAULT '0',
  `joined_at` datetime DEFAULT NULL,
  `is_report_submitted` tinyint(1) NOT NULL DEFAULT '0',
  `is_lc_approved` tinyint(1) NOT NULL DEFAULT '0',
  `report_text` varchar(1000) DEFAULT NULL,
  `report_link` varchar(200) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_circle_meet_attendees_ref_meet_id` (`meet_id`),
  KEY `fk_circle_meet_attendees_ref_user_id` (`user_id`),
  CONSTRAINT `fk_circle_meet_attendees_ref_meet_id` FOREIGN KEY (`meet_id`) REFERENCES `circle_meeting_log` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_circle_meet_attendees_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `circle_meeting_log`
--

DROP TABLE IF EXISTS `circle_meeting_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `circle_meeting_log` (
  `id` varchar(36) NOT NULL,
  `circle_id` varchar(36) NOT NULL,
  `meet_code` varchar(6) NOT NULL,
  `title` varchar(100) NOT NULL,
  `description` varchar(1000) NOT NULL,
  `mode` varchar(10) NOT NULL,
  `is_report_needed` tinyint(1) NOT NULL DEFAULT '1',
  `report_description` varchar(1000) DEFAULT NULL,
  `coord_x` float NOT NULL,
  `coord_y` float NOT NULL,
  `meet_place` varchar(255) NOT NULL,
  `meet_link` varchar(100) DEFAULT NULL,
  `meet_time` datetime NOT NULL,
  `duration` int NOT NULL,
  `is_report_submitted` tinyint(1) NOT NULL DEFAULT '0',
  `is_approved` tinyint(1) NOT NULL DEFAULT '0',
  `report_text` varchar(1000) DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `is_recurring` tinyint(1) NOT NULL DEFAULT '0',
  `recurrence_type` varchar(10) DEFAULT NULL,
  `recurrence` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_circle_meeting_log_ref_circle_id` (`circle_id`),
  KEY `fk_circle_meeting_log_ref_created_by` (`created_by`),
  CONSTRAINT `fk_circle_meeting_log_ref_circle_id` FOREIGN KEY (`circle_id`) REFERENCES `learning_circle` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_circle_meeting_log_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `college`
--

DROP TABLE IF EXISTS `college`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `college` (
  `id` varchar(36) NOT NULL,
  `level` int NOT NULL,
  `org_id` varchar(36) NOT NULL,
  `verified` tinyint(1) DEFAULT '0',
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `lead_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_college_ref_org_id` (`org_id`),
  KEY `fk_college_ref_created_by` (`created_by`),
  KEY `fk_college_ref_updated_by` (`updated_by`),
  KEY `fk_college_ref_lead` (`lead_id`),
  CONSTRAINT `fk_college_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_college_ref_lead` FOREIGN KEY (`lead_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_college_ref_org_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_college_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `country`
--

DROP TABLE IF EXISTS `country`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `country` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_country_ref_updated_by` (`updated_by`),
  KEY `fk_country_ref_created_by` (`created_by`),
  CONSTRAINT `fk_country_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_country_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `department`
--

DROP TABLE IF EXISTS `department`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `department` (
  `id` varchar(36) NOT NULL,
  `title` varchar(100) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_department_ref_updated_by` (`updated_by`),
  KEY `fk_department_ref_created_by` (`created_by`),
  CONSTRAINT `fk_department_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_department_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `device`
--

DROP TABLE IF EXISTS `device`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `device` (
  `id` varchar(36) NOT NULL,
  `browser` varchar(36) NOT NULL,
  `os` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `last_log_in` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_device_ref_user_id` (`user_id`),
  CONSTRAINT `fk_device_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `district`
--

DROP TABLE IF EXISTS `district`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `district` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `zone_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_district_ref_zone_id` (`zone_id`),
  KEY `fk_district_ref_updated_by` (`updated_by`),
  KEY `fk_district_ref_created_by` (`created_by`),
  CONSTRAINT `fk_district_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_district_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_district_ref_zone_id` FOREIGN KEY (`zone_id`) REFERENCES `zone` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `donation`
--

DROP TABLE IF EXISTS `donation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `donation` (
  `id` varchar(36) NOT NULL,
  `donor_id` varchar(36) NOT NULL,
  `order_id` varchar(100) DEFAULT NULL,
  `payment_id` varchar(100) DEFAULT NULL,
  `payment_method` varchar(50) DEFAULT NULL,
  `amount` decimal(12,2) NOT NULL,
  `currency` varchar(10) DEFAULT 'INR',
  `donation_type` varchar(20) NOT NULL,
  `is_paid` tinyint(1) DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `donation_name` varchar(100) DEFAULT NULL,
  `payment_status` varchar(30) DEFAULT 'COMPLETED',
  `reference_code` varchar(50) DEFAULT NULL,
  `proof_url` text,
  PRIMARY KEY (`id`),
  KEY `idx_donation_donor_id` (`donor_id`),
  KEY `idx_donation_order_id` (`order_id`),
  KEY `idx_donation_reference_code` (`reference_code`),
  KEY `idx_donation_payment_status` (`payment_status`),
  CONSTRAINT `fk_donation_donor` FOREIGN KEY (`donor_id`) REFERENCES `donor` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `donor`
--

DROP TABLE IF EXISTS `donor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `donor` (
  `id` varchar(36) NOT NULL,
  `payment_id` varchar(100) NOT NULL,
  `payment_method` varchar(100) NOT NULL,
  `amount` float NOT NULL,
  `currency` varchar(30) NOT NULL,
  `name` varchar(100) NOT NULL,
  `email` varchar(200) NOT NULL,
  `company` varchar(100) DEFAULT NULL,
  `phone_number` varchar(20) DEFAULT NULL,
  `pan_number` varchar(10) DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `address` text,
  `is_organisation` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `fk_donor_ref_created_by` (`created_by`),
  KEY `idx_donor_email` (`email`),
  CONSTRAINT `fk_donor_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dynamic_role`
--

DROP TABLE IF EXISTS `dynamic_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dynamic_role` (
  `id` varchar(36) NOT NULL,
  `type` varchar(50) NOT NULL,
  `role` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_dynamic_role_ref_role_id` (`role`),
  KEY `fk_role_management_ref_created_by` (`created_by`),
  KEY `fk_role_management_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_dynamic_role_ref_role_id` FOREIGN KEY (`role`) REFERENCES `role` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_role_management_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_role_management_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dynamic_user`
--

DROP TABLE IF EXISTS `dynamic_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `dynamic_user` (
  `id` varchar(36) NOT NULL,
  `type` varchar(50) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_dynamic_user_ref_user_id` (`user_id`),
  KEY `fk_dynamic_user_ref_created_by` (`created_by`),
  KEY `fk_dynamic_user_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_dynamic_user_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_dynamic_user_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_dynamic_user_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `events`
--

DROP TABLE IF EXISTS `events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `events` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `description` varchar(200) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_events_ref_updated_by` (`updated_by`),
  KEY `fk_events_ref_created_by` (`created_by`),
  CONSTRAINT `fk_events_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_events_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `forgot_password`
--

DROP TABLE IF EXISTS `forgot_password`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `forgot_password` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `expiry` datetime NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_forget_password_ref_user_id` (`user_id`),
  CONSTRAINT `fk_forget_password_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `hackathon`
--

DROP TABLE IF EXISTS `hackathon`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `hackathon` (
  `id` varchar(36) NOT NULL,
  `title` varchar(100) NOT NULL,
  `tagline` varchar(150) DEFAULT NULL,
  `description` varchar(5000) DEFAULT NULL,
  `participant_count` int DEFAULT NULL,
  `type` varchar(8) DEFAULT 'offline',
  `website` varchar(200) DEFAULT NULL,
  `org_id` varchar(36) DEFAULT NULL,
  `district_id` varchar(36) DEFAULT NULL,
  `place` varchar(255) DEFAULT NULL,
  `event_logo` varchar(200) DEFAULT NULL,
  `banner` varchar(200) DEFAULT NULL,
  `is_open_to_all` tinyint(1) DEFAULT NULL,
  `application_start` datetime DEFAULT NULL,
  `application_ends` datetime DEFAULT NULL,
  `event_start` datetime DEFAULT NULL,
  `event_end` datetime DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_hackathon_link_ref_org_id` (`org_id`),
  KEY `fk_hackathon_link_ref_district_id` (`district_id`),
  KEY `fk_hackathon_link_created_by` (`created_by`),
  KEY `fk_hackathon_link_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_hackathon_link_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_link_ref_district_id` FOREIGN KEY (`district_id`) REFERENCES `district` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_link_ref_org_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_link_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `hackathon_form`
--

DROP TABLE IF EXISTS `hackathon_form`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `hackathon_form` (
  `id` varchar(36) NOT NULL,
  `hackathon_id` varchar(36) NOT NULL,
  `field_name` varchar(255) NOT NULL,
  `field_type` varchar(50) NOT NULL,
  `is_required` tinyint(1) NOT NULL DEFAULT '0',
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_hackathon_form_ref_hackathon_id` (`hackathon_id`),
  KEY `fk_hackathon_form_ref_created_by` (`created_by`),
  KEY `fk_hackathon_form_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_hackathon_form_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_form_ref_hackathon_id` FOREIGN KEY (`hackathon_id`) REFERENCES `hackathon` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_form_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `hackathon_organiser_link`
--

DROP TABLE IF EXISTS `hackathon_organiser_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `hackathon_organiser_link` (
  `id` varchar(36) NOT NULL,
  `organiser_id` varchar(36) NOT NULL,
  `hackathon_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_hackathon_organiser_link_ref_organiser_id` (`organiser_id`),
  KEY `fk_hackathon_organiser_link_ref_hackathon_id` (`hackathon_id`),
  KEY `fk_hackathon_organiser_link_created_by` (`created_by`),
  KEY `fk_hackathon_organiser_link_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_hackathon_organiser_link_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_organiser_link_ref_hackathon_id` FOREIGN KEY (`hackathon_id`) REFERENCES `hackathon` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_organiser_link_ref_organiser_id` FOREIGN KEY (`organiser_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_organiser_link_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `hackathon_submission`
--

DROP TABLE IF EXISTS `hackathon_submission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `hackathon_submission` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `hackathon_id` varchar(36) NOT NULL,
  `data` varchar(2000) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_hackathon_submission_ref_user_id` (`user_id`),
  KEY `fk_hackathon_submission_ref_hackathon_id` (`hackathon_id`),
  KEY `fk_hackathon_submission_ref_updated_by` (`updated_by`),
  KEY `fk_hackathon_submission_ref_created_by` (`created_by`),
  CONSTRAINT `fk_hackathon_submission_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_submission_ref_hackathon_id` FOREIGN KEY (`hackathon_id`) REFERENCES `hackathon` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_submission_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_hackathon_submission_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `integration`
--

DROP TABLE IF EXISTS `integration`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `integration` (
  `id` varchar(36) NOT NULL,
  `name` varchar(255) NOT NULL,
  `token` varchar(400) NOT NULL,
  `auth_token` varchar(255) DEFAULT NULL,
  `base_url` varchar(255) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `integration_authorization`
--

DROP TABLE IF EXISTS `integration_authorization`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `integration_authorization` (
  `id` varchar(36) NOT NULL,
  `integration_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `integration_value` varchar(255) NOT NULL,
  `verified` tinyint(1) NOT NULL DEFAULT '0',
  `updated_at` datetime NOT NULL,
  `created_at` datetime NOT NULL,
  `additional_field` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `integration_value` (`integration_value`),
  UNIQUE KEY `unique_integration_per_user_integration_id` (`integration_id`,`user_id`,`integration_value`),
  KEY `fk_integration_authorization_user_id` (`user_id`),
  CONSTRAINT `fk_integration_authorization_integration_id` FOREIGN KEY (`integration_id`) REFERENCES `integration` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_integration_authorization_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `interest_group`
--

DROP TABLE IF EXISTS `interest_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `interest_group` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `code` varchar(5) NOT NULL,
  `icon` varchar(10) NOT NULL,
  `category` varchar(20) NOT NULL DEFAULT 'others',
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `about` text,
  `prerequisites` text,
  `resource` text,
  `career_opportunities` text,
  `top_blogs` text,
  `people_to_follow` text,
  `leads` text,
  `mentors` text,
  `thinktank` text,
  `office_hours` varchar(200) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `code` (`code`),
  KEY `fk_interest_group_ref_updated_by` (`updated_by`),
  KEY `fk_interest_group_ref_created_by` (`created_by`),
  CONSTRAINT `fk_interest_group_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_interest_group_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `intro_task_log`
--

DROP TABLE IF EXISTS `intro_task_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `intro_task_log` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `progress` int NOT NULL,
  `channel_id` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_intro_task_log_ref_created_by` (`created_by`),
  KEY `fk_intro_task_log_ref_updated_by` (`updated_by`),
  KEY `fk_intro_task_log_ref_user_id` (`user_id`),
  CONSTRAINT `fk_intro_task_log_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_intro_task_log_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_intro_task_log_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `karma_activity_log`
--

DROP TABLE IF EXISTS `karma_activity_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `karma_activity_log` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `karma` int NOT NULL DEFAULT '0',
  `task_id` varchar(36) NOT NULL,
  `task_message_id` varchar(36) DEFAULT NULL,
  `lobby_message_id` varchar(36) DEFAULT NULL,
  `dm_message_id` varchar(36) DEFAULT NULL,
  `peer_approved` tinyint(1) DEFAULT NULL,
  `peer_approved_by` varchar(36) DEFAULT NULL,
  `appraiser_approved` tinyint(1) DEFAULT NULL,
  `appraiser_approved_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_karma_activity_log_ref_user_id` (`user_id`),
  KEY `fk_karma_activity_log_ref_task_id` (`task_id`),
  KEY `fk_karma_activity_log_ref_updated_by` (`updated_by`),
  KEY `fk_karma_activity_log_ref_created_by` (`created_by`),
  CONSTRAINT `fk_karma_activity_log_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_karma_activity_log_ref_task_id` FOREIGN KEY (`task_id`) REFERENCES `task_list` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_karma_activity_log_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_karma_activity_log_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `launchpad`
--

DROP TABLE IF EXISTS `launchpad`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `launchpad` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `launchpad_id` varchar(100) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `launchpad_id` (`launchpad_id`),
  KEY `fk_launchpad_user_id` (`user_id`),
  KEY `fk_launchpad_created_by` (`created_by`),
  KEY `fk_launchpad_updated_by` (`updated_by`),
  CONSTRAINT `fk_launchpad_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_launchpad_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_launchpad_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `launchpad_companies`
--

DROP TABLE IF EXISTS `launchpad_companies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `launchpad_companies` (
  `id` varchar(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `website` varchar(200) DEFAULT NULL,
  `description` text,
  `address` varchar(255) DEFAULT NULL,
  `poc_name` varchar(100) NOT NULL,
  `poc_role` varchar(100) NOT NULL,
  `poc_email` varchar(100) NOT NULL,
  `poc_phone` varchar(20) NOT NULL,
  `username` varchar(50) NOT NULL,
  `password` varchar(255) NOT NULL,
  `is_verified` tinyint(1) DEFAULT '0',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `reset_token` varchar(100) DEFAULT NULL,
  `reset_token_expires` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `username` (`username`),
  KEY `idx_launchpad_companies_reset_token` (`reset_token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `launchpad_job_applications`
--

DROP TABLE IF EXISTS `launchpad_job_applications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `launchpad_job_applications` (
  `id` varchar(36) NOT NULL,
  `job_id` varchar(36) NOT NULL,
  `student_id` varchar(36) NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'invited',
  `resume_link` varchar(500) DEFAULT NULL,
  `linkedin_link` varchar(500) DEFAULT NULL,
  `portfolio_link` varchar(500) DEFAULT NULL,
  `cover_letter` text,
  `other_link` varchar(500) DEFAULT NULL,
  `interview_date` datetime DEFAULT NULL,
  `interview_time` time DEFAULT NULL,
  `interview_platform` varchar(255) DEFAULT NULL,
  `interview_link` varchar(500) DEFAULT NULL,
  `interview_type` varchar(100) DEFAULT NULL,
  `invited_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `applied_at` datetime DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uniq_job_student` (`job_id`,`student_id`),
  KEY `fk_student` (`student_id`),
  CONSTRAINT `fk_job` FOREIGN KEY (`job_id`) REFERENCES `launchpad_jobs` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_student` FOREIGN KEY (`student_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `launchpad_job_tasks`
--

DROP TABLE IF EXISTS `launchpad_job_tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `launchpad_job_tasks` (
  `id` varchar(36) NOT NULL,
  `task_description` text NOT NULL,
  `hashtags` varchar(255) DEFAULT NULL,
  `is_verified` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `launchpad_jobs`
--

DROP TABLE IF EXISTS `launchpad_jobs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `launchpad_jobs` (
  `id` varchar(36) NOT NULL,
  `company_id` varchar(36) NOT NULL,
  `recruiter_id` varchar(36) NOT NULL,
  `title` varchar(100) NOT NULL,
  `skills` varchar(255) DEFAULT NULL,
  `experience` varchar(255) DEFAULT NULL,
  `domain` varchar(255) NOT NULL,
  `interest_groups` varchar(255) NOT NULL,
  `task_description` text,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `opening_type` varchar(50) DEFAULT NULL,
  `location` varchar(255) DEFAULT NULL,
  `salary_range` varchar(50) DEFAULT NULL,
  `job_type` varchar(50) DEFAULT NULL,
  `minimum_karma` int DEFAULT '0',
  `task_id` varchar(36) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_launchpad_jobs_company_id` (`company_id`),
  KEY `fk_launchpad_jobs_recruiter_id` (`recruiter_id`),
  KEY `fk_launchpad_jobs_task` (`task_id`),
  CONSTRAINT `fk_launchpad_jobs_company_id` FOREIGN KEY (`company_id`) REFERENCES `launchpad_companies` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_launchpad_jobs_recruiter_id` FOREIGN KEY (`recruiter_id`) REFERENCES `launchpad_recruiters` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_launchpad_jobs_task` FOREIGN KEY (`task_id`) REFERENCES `launchpad_job_tasks` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `launchpad_recruiters`
--

DROP TABLE IF EXISTS `launchpad_recruiters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `launchpad_recruiters` (
  `id` varchar(36) NOT NULL,
  `company_id` varchar(36) NOT NULL,
  `name` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `phone` varchar(20) NOT NULL,
  `password` varchar(255) NOT NULL,
  `role` varchar(50) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `reset_token` varchar(100) DEFAULT NULL,
  `reset_token_expires` timestamp NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `fk_launchpad_recruiters_company_id` (`company_id`),
  KEY `idx_launchpad_recruiters_reset_token` (`reset_token`),
  CONSTRAINT `fk_launchpad_recruiters_company_id` FOREIGN KEY (`company_id`) REFERENCES `launchpad_companies` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `launchpad_user`
--

DROP TABLE IF EXISTS `launchpad_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `launchpad_user` (
  `id` varchar(36) NOT NULL,
  `email` varchar(255) NOT NULL,
  `phone_number` varchar(15) DEFAULT NULL,
  `full_name` varchar(255) DEFAULT NULL,
  `district` varchar(100) DEFAULT NULL,
  `zone` varchar(100) DEFAULT NULL,
  `role` varchar(20) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `launchpad_user_college_link`
--

DROP TABLE IF EXISTS `launchpad_user_college_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `launchpad_user_college_link` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `college_id` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by_id` varchar(36) NOT NULL,
  `updated_by_id` varchar(36) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_launchpad_user_college_link_user_id` (`user_id`),
  KEY `fk_launchpad_user_college_link_college_id` (`college_id`),
  KEY `fk_launchpad_user_college_link_created_by_id` (`created_by_id`),
  KEY `fk_launchpad_user_college_link_updated_by_id` (`updated_by_id`),
  CONSTRAINT `fk_launchpad_user_college_link_college_id` FOREIGN KEY (`college_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_launchpad_user_college_link_created_by_id` FOREIGN KEY (`created_by_id`) REFERENCES `launchpad_user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_launchpad_user_college_link_updated_by_id` FOREIGN KEY (`updated_by_id`) REFERENCES `launchpad_user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_launchpad_user_college_link_user_id` FOREIGN KEY (`user_id`) REFERENCES `launchpad_user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `learning_circle`
--

DROP TABLE IF EXISTS `learning_circle`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `learning_circle` (
  `id` varchar(36) NOT NULL,
  `title` varchar(100) NOT NULL,
  `description` varchar(1000) NOT NULL,
  `name` varchar(255) DEFAULT NULL,
  `circle_code` varchar(15) DEFAULT NULL,
  `ig_id` varchar(36) NOT NULL,
  `org_id` varchar(36) DEFAULT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `circle_code` (`circle_code`),
  KEY `fk_learning_circle_ref_college_id` (`org_id`),
  KEY `fk_learning_circle_ref_created_by` (`created_by`),
  KEY `fk_learning_circle_ref_interest_group_id` (`ig_id`),
  CONSTRAINT `fk_learning_circle_ref_college_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_learning_circle_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_learning_circle_ref_interest_group_id` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `level`
--

DROP TABLE IF EXISTS `level`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `level` (
  `id` varchar(36) NOT NULL,
  `level_order` int NOT NULL,
  `name` varchar(36) NOT NULL,
  `karma` int NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `fk_level_ref_created_by` (`created_by`),
  KEY `fk_level_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_level_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_level_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `login_attempts_log`
--

DROP TABLE IF EXISTS `login_attempts_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `login_attempts_log` (
  `id` varchar(36) NOT NULL,
  `email_muid` varchar(200) NOT NULL,
  `status` varchar(36) NOT NULL,
  `type` varchar(36) NOT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `browser` varchar(255) DEFAULT NULL,
  `os` varchar(255) DEFAULT NULL,
  `version` varchar(255) DEFAULT NULL,
  `device_type` varchar(255) DEFAULT NULL,
  `city` varchar(36) DEFAULT NULL,
  `region` varchar(36) DEFAULT NULL,
  `country` varchar(36) DEFAULT NULL,
  `location` varchar(36) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mucoin_activity_log`
--

DROP TABLE IF EXISTS `mucoin_activity_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mucoin_activity_log` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `coin` float NOT NULL,
  `status` varchar(36) NOT NULL,
  `task_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_mucoin_activity_log_ref_created_by` (`created_by`),
  KEY `fk_mucoin_activity_log_ref_updated_by` (`updated_by`),
  KEY `fk_mucoin_activity_log_ref_task_id` (`task_id`),
  KEY `fk_mucoin_activity_log_ref_user_id` (`user_id`),
  CONSTRAINT `fk_mucoin_activity_log_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mucoin_activity_log_ref_task_id` FOREIGN KEY (`task_id`) REFERENCES `task_list` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mucoin_activity_log_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mucoin_activity_log_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `mucoin_invite_log`
--

DROP TABLE IF EXISTS `mucoin_invite_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `mucoin_invite_log` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `email` varchar(200) NOT NULL,
  `invite_code` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_mucoin_invite_log_ref_user_id` (`user_id`),
  KEY `fk_mucoin_invite_log_created_by` (`created_by`),
  CONSTRAINT `fk_mucoin_invite_log_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_mucoin_invite_log_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notification`
--

DROP TABLE IF EXISTS `notification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notification` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `title` varchar(50) NOT NULL,
  `description` varchar(200) NOT NULL,
  `button` varchar(10) DEFAULT NULL,
  `url` varchar(100) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_notification_ref_user_id` (`user_id`),
  KEY `fk_notification_ref_created_by` (`created_by`),
  CONSTRAINT `fk_notification_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_notification_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `org_affiliation`
--

DROP TABLE IF EXISTS `org_affiliation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `org_affiliation` (
  `id` varchar(36) NOT NULL,
  `title` varchar(75) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_org_affiliation_ref_updated_by` (`updated_by`),
  KEY `fk_org_affiliation_ref_created_by` (`created_by`),
  CONSTRAINT `fk_org_affiliation_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_org_affiliation_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `org_discord_link`
--

DROP TABLE IF EXISTS `org_discord_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `org_discord_link` (
  `id` varchar(36) NOT NULL,
  `discord_id` varchar(36) NOT NULL,
  `org_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `discord_id` (`discord_id`),
  UNIQUE KEY `org_id` (`org_id`),
  KEY `fk_org_discord_link_created_by` (`created_by`),
  KEY `fk_org_discord_link_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_college_discord_link_ref_org_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_org_discord_link_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_org_discord_link_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `org_karma_log`
--

DROP TABLE IF EXISTS `org_karma_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `org_karma_log` (
  `id` varchar(36) NOT NULL,
  `org_id` varchar(36) NOT NULL,
  `karma` int NOT NULL DEFAULT '0',
  `type` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_org_karma_log_ref_org_id` (`org_id`),
  KEY `fk_org_karma_log_ref_type` (`type`),
  KEY `fk_org_karma_log_ref_created_by` (`created_by`),
  KEY `fk_org_karma_log_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_org_karma_log_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_org_karma_log_ref_org_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_org_karma_log_ref_type` FOREIGN KEY (`type`) REFERENCES `org_karma_type` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_org_karma_log_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `org_karma_type`
--

DROP TABLE IF EXISTS `org_karma_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `org_karma_type` (
  `id` varchar(36) NOT NULL,
  `title` varchar(75) NOT NULL,
  `karma` int NOT NULL DEFAULT '0',
  `description` varchar(200) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_org_karma_type_ref_updated_by` (`updated_by`),
  KEY `fk_org_karma_type_ref_created_by` (`created_by`),
  CONSTRAINT `fk_org_karma_type_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_org_karma_type_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `organization`
--

DROP TABLE IF EXISTS `organization`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `organization` (
  `id` varchar(36) NOT NULL,
  `title` varchar(100) NOT NULL,
  `code` varchar(12) NOT NULL,
  `org_type` varchar(25) NOT NULL,
  `affiliation_id` varchar(36) DEFAULT NULL,
  `district_id` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `cached_total_karma` int NOT NULL DEFAULT '0',
  `cached_member_count` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  KEY `fk_organization_ref_affiliation_id` (`affiliation_id`),
  KEY `fk_organization_ref_district_id` (`district_id`),
  KEY `fk_organization_ref_updated_by` (`updated_by`),
  KEY `fk_organization_ref_created_by` (`created_by`),
  KEY `idx_organization_org_type_karma` (`org_type`,`cached_total_karma`),
  KEY `idx_organization_org_type_members` (`org_type`,`cached_member_count`),
  CONSTRAINT `fk_organization_ref_affiliation_id` FOREIGN KEY (`affiliation_id`) REFERENCES `org_affiliation` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_organization_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_organization_ref_district_id` FOREIGN KEY (`district_id`) REFERENCES `district` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_organization_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `orgbot_channel`
--

DROP TABLE IF EXISTS `orgbot_channel`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orgbot_channel` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `discord_id` varchar(36) NOT NULL,
  `org_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_orgbot_channel_ref_org_id` (`org_id`),
  KEY `fk_orgbot_channel_ref_updated_by` (`updated_by`),
  KEY `fk_orgbot_channel_ref_created_by` (`created_by`),
  CONSTRAINT `fk_orgbot_channel_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_orgbot_channel_ref_org_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_orgbot_channel_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `orgbot_karma_log`
--

DROP TABLE IF EXISTS `orgbot_karma_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orgbot_karma_log` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `karma` int NOT NULL DEFAULT '0',
  `task_id` varchar(36) NOT NULL,
  `task_message_id` varchar(36) DEFAULT NULL,
  `lobby_message_id` varchar(36) DEFAULT NULL,
  `dm_message_id` varchar(36) DEFAULT NULL,
  `peer_approved` tinyint(1) DEFAULT NULL,
  `peer_approved_by` varchar(36) DEFAULT NULL,
  `appraiser_approved` tinyint(1) DEFAULT NULL,
  `appraiser_approved_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_orgbot_karma_log_ref_user_id` (`user_id`),
  KEY `fk_orgbot_karma_log_ref_task_id` (`task_id`),
  KEY `fk_orgbot_karma_log_ref_updated_by` (`updated_by`),
  KEY `fk_orgbot_karma_log_ref_created_by` (`created_by`),
  CONSTRAINT `fk_orgbot_karma_log_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_orgbot_karma_log_ref_task_id` FOREIGN KEY (`task_id`) REFERENCES `orgbot_tasks` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_orgbot_karma_log_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_orgbot_karma_log_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `orgbot_tasks`
--

DROP TABLE IF EXISTS `orgbot_tasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `orgbot_tasks` (
  `id` varchar(36) NOT NULL,
  `title` varchar(75) NOT NULL,
  `hashtag` varchar(75) NOT NULL,
  `description` varchar(200) NOT NULL,
  `org_id` varchar(36) NOT NULL,
  `karma` int DEFAULT NULL,
  `usage_count` int DEFAULT NULL,
  `level_order` int DEFAULT NULL,
  `channel_id` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_orgbot_tasks_ref_updated_by` (`updated_by`),
  KEY `fk_orgbot_tasks_ref_created_by` (`created_by`),
  KEY `fk_orgbot_tasks_ref_channel_id` (`channel_id`),
  CONSTRAINT `fk_orgbot_tasks_ref_channel_id` FOREIGN KEY (`channel_id`) REFERENCES `orgbot_channel` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_orgbot_tasks_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_orgbot_tasks_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `otp_verification`
--

DROP TABLE IF EXISTS `otp_verification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `otp_verification` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `otp` int NOT NULL,
  `expiry` datetime NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_otp_verification_ref_user_id` (`user_id`),
  CONSTRAINT `fk_otp_verification_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `quiz`
--

DROP TABLE IF EXISTS `quiz`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `quiz` (
  `id` varchar(36) NOT NULL,
  `name` varchar(255) NOT NULL,
  `description` text,
  `pass_rate` int DEFAULT '70',
  `ordered` tinyint(1) DEFAULT '0',
  `name_long` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `quiz_answers`
--

DROP TABLE IF EXISTS `quiz_answers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `quiz_answers` (
  `id` varchar(36) NOT NULL,
  `question_id` char(36) NOT NULL,
  `answer` text NOT NULL,
  `is_correct` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `question_id` (`question_id`),
  CONSTRAINT `quiz_answers_ibfk_1` FOREIGN KEY (`question_id`) REFERENCES `quiz_questions` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `quiz_log`
--

DROP TABLE IF EXISTS `quiz_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `quiz_log` (
  `id` varchar(36) NOT NULL,
  `discord_id` varchar(32) NOT NULL,
  `quiz_id` char(36) NOT NULL,
  `attempt` int DEFAULT '1',
  `passed` tinyint(1) DEFAULT '0',
  `score` int DEFAULT NULL,
  `attempted_on` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `quiz_id` (`quiz_id`),
  CONSTRAINT `quiz_log_ibfk_1` FOREIGN KEY (`quiz_id`) REFERENCES `quiz` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `quiz_questions`
--

DROP TABLE IF EXISTS `quiz_questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `quiz_questions` (
  `id` varchar(36) NOT NULL,
  `quiz_id` char(36) NOT NULL,
  `question` text NOT NULL,
  `order_num` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `quiz_id` (`quiz_id`),
  CONSTRAINT `quiz_questions_ibfk_1` FOREIGN KEY (`quiz_id`) REFERENCES `quiz` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `quiz_sessions`
--

DROP TABLE IF EXISTS `quiz_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `quiz_sessions` (
  `id` varchar(36) NOT NULL,
  `discord_id` varchar(32) NOT NULL,
  `channel_id` varchar(32) NOT NULL,
  `current_question` char(36) DEFAULT NULL,
  `active` tinyint(1) DEFAULT '1',
  `passed` tinyint(1) DEFAULT '0',
  `quiz_id` char(36) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `quiz_id` (`quiz_id`),
  CONSTRAINT `quiz_sessions_ibfk_1` FOREIGN KEY (`quiz_id`) REFERENCES `quiz` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `role`
--

DROP TABLE IF EXISTS `role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `role` (
  `id` varchar(36) NOT NULL,
  `title` varchar(75) NOT NULL,
  `description` varchar(300) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `title` (`title`),
  KEY `fk_role_ref_updated_by` (`updated_by`),
  KEY `fk_role_ref_created_by` (`created_by`),
  CONSTRAINT `fk_role_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_role_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `socials`
--

DROP TABLE IF EXISTS `socials`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `socials` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `github` varchar(60) DEFAULT NULL,
  `facebook` varchar(60) DEFAULT NULL,
  `instagram` varchar(60) DEFAULT NULL,
  `linkedin` varchar(60) DEFAULT NULL,
  `dribble` varchar(60) DEFAULT NULL,
  `behance` varchar(60) DEFAULT NULL,
  `stackoverflow` varchar(60) DEFAULT NULL,
  `medium` varchar(60) DEFAULT NULL,
  `hackerrank` varchar(60) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_socials_ref_user_id` (`user_id`),
  KEY `fk_socials_ref_created_by` (`created_by`),
  KEY `fk_socials_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_socials_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_socials_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_socials_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `state`
--

DROP TABLE IF EXISTS `state`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `state` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `country_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_state_ref_country_id` (`country_id`),
  KEY `fk_state_ref_updated_by` (`updated_by`),
  KEY `fk_state_ref_created_by` (`created_by`),
  CONSTRAINT `fk_state_ref_country_id` FOREIGN KEY (`country_id`) REFERENCES `country` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_state_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_state_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `system_setting`
--

DROP TABLE IF EXISTS `system_setting`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_setting` (
  `key` varchar(100) NOT NULL,
  `value` varchar(100) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `task_list`
--

DROP TABLE IF EXISTS `task_list`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `task_list` (
  `id` varchar(36) NOT NULL,
  `hashtag` varchar(75) NOT NULL,
  `discord_link` varchar(200) DEFAULT NULL,
  `title` varchar(75) NOT NULL,
  `description` text,
  `karma` int DEFAULT NULL,
  `channel_id` varchar(36) DEFAULT NULL,
  `type_id` varchar(36) NOT NULL,
  `org_id` varchar(36) DEFAULT NULL,
  `level_id` varchar(36) DEFAULT NULL,
  `ig_id` varchar(36) DEFAULT NULL,
  `active` tinyint(1) NOT NULL DEFAULT '1',
  `variable_karma` tinyint(1) NOT NULL DEFAULT '0',
  `usage_count` int DEFAULT '1',
  `event` varchar(50) DEFAULT NULL,
  `bonus_time` datetime DEFAULT NULL,
  `bonus_karma` int DEFAULT '0',
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_task_list_ref_level_id` (`level_id`),
  KEY `fk_task_list_ref_ig_id` (`ig_id`),
  KEY `fk_task_list_ref_channel_id` (`channel_id`),
  KEY `fk_task_list_ref_type_id` (`type_id`),
  KEY `fk_task_list_ref_org_id` (`org_id`),
  KEY `fk_task_list_ref_updated_by` (`updated_by`),
  KEY `fk_task_list_ref_created_by` (`created_by`),
  CONSTRAINT `fk_task_list_ref_channel_id` FOREIGN KEY (`channel_id`) REFERENCES `channel` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_list_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_list_ref_ig_id` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_list_ref_level_id` FOREIGN KEY (`level_id`) REFERENCES `level` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_list_ref_org_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_list_ref_type_id` FOREIGN KEY (`type_id`) REFERENCES `task_type` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_list_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `task_type`
--

DROP TABLE IF EXISTS `task_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `task_type` (
  `id` varchar(36) NOT NULL,
  `title` varchar(75) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_task_type_ref_updated_by` (`updated_by`),
  KEY `fk_task_type_ref_created_by` (`created_by`),
  CONSTRAINT `fk_task_type_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_task_type_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `unverified_organization`
--

DROP TABLE IF EXISTS `unverified_organization`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `unverified_organization` (
  `id` varchar(36) NOT NULL,
  `title` varchar(100) NOT NULL,
  `org_type` varchar(25) NOT NULL,
  `graduation_year` int DEFAULT NULL,
  `department_id` varchar(36) DEFAULT NULL,
  `verified` tinyint(1) DEFAULT NULL,
  `verified_by` varchar(36) DEFAULT NULL,
  `verified_at` datetime DEFAULT NULL,
  `org_id` varchar(36) DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_unverified_organizations_verified_by_user` (`verified_by`),
  KEY `fk_unverified_organizations_org_id_organization` (`org_id`),
  KEY `fk_unverified_organizations_department_id_department` (`department_id`),
  KEY `fk_unverified_organizations_created_by_user` (`created_by`),
  CONSTRAINT `fk_unverified_organizations_created_by_user` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_unverified_organizations_department_id_department` FOREIGN KEY (`department_id`) REFERENCES `department` (`id`),
  CONSTRAINT `fk_unverified_organizations_org_id_organization` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`),
  CONSTRAINT `fk_unverified_organizations_verified_by_user` FOREIGN KEY (`verified_by`) REFERENCES `user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `url_shortener`
--

DROP TABLE IF EXISTS `url_shortener`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `url_shortener` (
  `id` varchar(36) NOT NULL,
  `title` varchar(100) NOT NULL,
  `short_url` varchar(100) NOT NULL,
  `long_url` varchar(500) NOT NULL,
  `count` int NOT NULL DEFAULT '0',
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `short_url` (`short_url`),
  KEY `fk_url_shorten_ref_updated_by` (`updated_by`),
  KEY `fk_url_shorten_ref_created_by` (`created_by`),
  CONSTRAINT `fk_url_shorten_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_url_shorten_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `url_shortener_tracker`
--

DROP TABLE IF EXISTS `url_shortener_tracker`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `url_shortener_tracker` (
  `id` varchar(36) NOT NULL,
  `url_shortener_id` varchar(36) DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `browser` varchar(255) DEFAULT NULL,
  `operating_system` varchar(255) DEFAULT NULL,
  `version` varchar(255) DEFAULT NULL,
  `device_type` varchar(255) DEFAULT NULL,
  `city` varchar(36) DEFAULT NULL,
  `region` varchar(36) DEFAULT NULL,
  `country` varchar(36) DEFAULT NULL,
  `location` varchar(36) DEFAULT NULL,
  `referrer` varchar(36) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_url_shortener_tracker_ref_url_shortener_id` (`url_shortener_id`),
  CONSTRAINT `fk_url_shortener_tracker_ref_url_shortener_id` FOREIGN KEY (`url_shortener_id`) REFERENCES `url_shortener` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user`
--

DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `id` varchar(36) NOT NULL,
  `full_name` varchar(150) NOT NULL,
  `discord_id` varchar(36) DEFAULT NULL,
  `muid` varchar(100) NOT NULL,
  `email` varchar(200) NOT NULL,
  `password` varchar(200) DEFAULT NULL,
  `mobile` varchar(15) DEFAULT NULL,
  `gender` varchar(10) DEFAULT NULL,
  `dob` date DEFAULT NULL,
  `admin` tinyint(1) NOT NULL DEFAULT '0',
  `exist_in_guild` tinyint(1) NOT NULL DEFAULT '0',
  `created_at` datetime NOT NULL,
  `district_id` varchar(36) DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `suspended_at` datetime DEFAULT NULL,
  `suspended_by` varchar(36) DEFAULT NULL,
  `interested_in_work` tinyint(1) DEFAULT '0',
  `interested_in_gig_work` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `muid` (`muid`),
  UNIQUE KEY `email` (`email`),
  UNIQUE KEY `discord_id` (`discord_id`),
  KEY `fk_user_ref_district_id` (`district_id`),
  KEY `fk_user_ref_deleted_by` (`deleted_by`),
  KEY `fk_user_ref_suspended_by` (`suspended_by`),
  CONSTRAINT `fk_user_ref_deleted_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_ref_district_id` FOREIGN KEY (`district_id`) REFERENCES `district` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_ref_suspended_by` FOREIGN KEY (`suspended_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_achievements_log`
--

DROP TABLE IF EXISTS `user_achievements_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_achievements_log` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `achievement_id` varchar(36) NOT NULL,
  `is_issued` tinyint(1) NOT NULL DEFAULT '0',
  `vc_url` varchar(100) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_achievements_updated_by` (`updated_by`),
  KEY `fk_user_achievements_created_by` (`created_by`),
  KEY `fk_user_achievements_user_id` (`user_id`),
  KEY `fk_user_achievements_achievement_id` (`achievement_id`),
  CONSTRAINT `fk_user_achievements_achievement_id` FOREIGN KEY (`achievement_id`) REFERENCES `achievement` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_achievements_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_achievements_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_achievements_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_circle_link`
--

DROP TABLE IF EXISTS `user_circle_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_circle_link` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `circle_id` varchar(36) NOT NULL,
  `lead` tinyint(1) DEFAULT NULL,
  `is_invited` tinyint DEFAULT '0',
  `accepted` tinyint(1) DEFAULT NULL,
  `accepted_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_circle_link_ref_circle_id` (`circle_id`),
  KEY `fk_user_circle_link_ref_user_id` (`user_id`),
  CONSTRAINT `fk_user_circle_link_ref_circle_id` FOREIGN KEY (`circle_id`) REFERENCES `learning_circle` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_circle_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_coupon_link`
--

DROP TABLE IF EXISTS `user_coupon_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_coupon_link` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(75) NOT NULL,
  `coupon` varchar(15) NOT NULL,
  `type` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_coupon_link_ref_created_by` (`created_by`),
  KEY `fk_user_coupon_link_ref_user_id` (`user_id`),
  CONSTRAINT `fk_user_coupon_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_coupon_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_domains`
--

DROP TABLE IF EXISTS `user_domains`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_domains` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `domain_name` varchar(100) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_domains_user_id` (`user_id`),
  CONSTRAINT `fk_user_domains_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_endgoals`
--

DROP TABLE IF EXISTS `user_endgoals`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_endgoals` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `endgoal_name` varchar(100) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_endgoals_user_id` (`user_id`),
  CONSTRAINT `fk_user_endgoals_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_ig_link`
--

DROP TABLE IF EXISTS `user_ig_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_ig_link` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `ig_id` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_ig_link_ref_user_id` (`user_id`),
  KEY `fk_user_ig_link_ref_ig_id` (`ig_id`),
  KEY `fk_user_ig_link_ref_created_by` (`created_by`),
  CONSTRAINT `fk_user_ig_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_ig_link_ref_ig_id` FOREIGN KEY (`ig_id`) REFERENCES `interest_group` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_ig_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_lvl_link`
--

DROP TABLE IF EXISTS `user_lvl_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_lvl_link` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(75) NOT NULL,
  `level_id` varchar(75) NOT NULL,
  `grit` int NOT NULL DEFAULT '50',
  `last_level_down_at` datetime DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `fk_user_lvl_link_ref_created_by` (`created_by`),
  KEY `fk_user_lvl_link_ref_level_id` (`level_id`),
  KEY `fk_user_lvl_link_ref_updated_by` (`updated_by`),
  CONSTRAINT `fk_user_lvl_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_lvl_link_ref_level_id` FOREIGN KEY (`level_id`) REFERENCES `level` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_lvl_link_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_lvl_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_lvl_log`
--

DROP TABLE IF EXISTS `user_lvl_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_lvl_log` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(75) NOT NULL,
  `level_id` varchar(75) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_lvl_log_ref_level_id` (`level_id`),
  KEY `fk_user_lvl_log_ref_user_id` (`user_id`),
  CONSTRAINT `fk_user_lvl_log_ref_level_id` FOREIGN KEY (`level_id`) REFERENCES `level` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_lvl_log_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_mentor`
--

DROP TABLE IF EXISTS `user_mentor`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_mentor` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `about` varchar(1000) DEFAULT NULL,
  `reason` varchar(1000) DEFAULT NULL,
  `hours` varchar(20) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime DEFAULT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_mentor_ref_user` (`user_id`),
  KEY `fk_user_mentor_ref_updated_by` (`updated_by`),
  KEY `fk_user_mentor_ref_created_by` (`created_by`),
  CONSTRAINT `fk_user_mentor_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_mentor_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_mentor_ref_user` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_organization_link`
--

DROP TABLE IF EXISTS `user_organization_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_organization_link` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `org_id` varchar(36) NOT NULL,
  `department_id` varchar(36) DEFAULT NULL,
  `graduation_year` varchar(10) DEFAULT NULL,
  `verified` tinyint(1) NOT NULL DEFAULT '0',
  `is_alumni` tinyint(1) DEFAULT '0',
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_organization_link_ref_department_id` (`department_id`),
  KEY `fk_user_organization_link_ref_user_id` (`user_id`),
  KEY `fk_user_organization_link_ref_org_id` (`org_id`),
  KEY `fk_user_organization_link_ref_created_by` (`created_by`),
  KEY `idx_user_organization_link_org_verified` (`org_id`,`verified`),
  CONSTRAINT `fk_user_organization_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_organization_link_ref_department_id` FOREIGN KEY (`department_id`) REFERENCES `department` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_organization_link_ref_org_id` FOREIGN KEY (`org_id`) REFERENCES `organization` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_organization_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_referral_link`
--

DROP TABLE IF EXISTS `user_referral_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_referral_link` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `referral_id` varchar(36) NOT NULL,
  `is_coin` tinyint(1) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_referral_link_ref_user_id` (`user_id`),
  KEY `fk_user_referral_link_referral_id` (`referral_id`),
  KEY `fk_user_referral_link_ref_updated_by` (`updated_by`),
  KEY `fk_user_referral_link_ref_created_by` (`created_by`),
  CONSTRAINT `fk_user_referral_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_referral_link_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_referral_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_referral_link_referral_id` FOREIGN KEY (`referral_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_role_link`
--

DROP TABLE IF EXISTS `user_role_link`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_role_link` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `role_id` varchar(36) NOT NULL,
  `verified` tinyint(1) NOT NULL DEFAULT '0',
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_user_role_link_ref_user_id` (`user_id`),
  KEY `fk_user_role_link_ref_role_id` (`role_id`),
  KEY `fk_user_role_link_ref_created_by` (`created_by`),
  CONSTRAINT `fk_user_role_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_role_link_ref_role_id` FOREIGN KEY (`role_id`) REFERENCES `role` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_role_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_settings`
--

DROP TABLE IF EXISTS `user_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_settings` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `is_public` tinyint(1) NOT NULL DEFAULT '0',
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `is_userterms_approved` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `fk_user_settings_ref_user_id` (`user_id`),
  KEY `fk_user_settings_created_by` (`created_by`),
  KEY `fk_user_settings_updated_by` (`updated_by`),
  CONSTRAINT `fk_user_settings_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_settings_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_settings_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `voucher_log`
--

DROP TABLE IF EXISTS `voucher_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `voucher_log` (
  `id` varchar(36) NOT NULL,
  `code` varchar(15) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `task_id` varchar(36) NOT NULL,
  `karma` int NOT NULL DEFAULT '0',
  `mail` varchar(200) NOT NULL,
  `week` varchar(2) DEFAULT NULL,
  `month` varchar(10) NOT NULL,
  `claimed` tinyint(1) NOT NULL,
  `event` varchar(50) DEFAULT NULL,
  `description` varchar(50) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_voucher_log_ref_created_by` (`created_by`),
  KEY `fk_voucher_log_ref_task_id` (`task_id`),
  KEY `fk_voucher_log_ref_user_id` (`user_id`),
  CONSTRAINT `fk_voucher_log_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_voucher_log_ref_task_id` FOREIGN KEY (`task_id`) REFERENCES `task_list` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_voucher_log_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wallet`
--

DROP TABLE IF EXISTS `wallet`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wallet` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `karma` bigint NOT NULL DEFAULT '0',
  `karma_last_updated_at` datetime DEFAULT NULL,
  `coin` float NOT NULL DEFAULT '0',
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `fk_total_karma_ref_updated_by` (`updated_by`),
  KEY `fk_total_karma_ref_created_by` (`created_by`),
  CONSTRAINT `fk_total_karma_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_total_karma_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_total_karma_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `zone`
--

DROP TABLE IF EXISTS `zone`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `zone` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `state_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_zone_ref_state_id` (`state_id`),
  KEY `fk_zone_ref_updated_by` (`updated_by`),
  KEY `fk_zone_ref_created_by` (`created_by`),
  CONSTRAINT `fk_zone_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_zone_ref_state_id` FOREIGN KEY (`state_id`) REFERENCES `state` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_zone_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `comic_comment`
--

DROP TABLE IF EXISTS `comic_comment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `comic_comment` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `chapter_id` varchar(36) DEFAULT NULL,
  `parent_id` varchar(36) DEFAULT NULL,
  `user_id` varchar(36) NOT NULL,
  `message` text NOT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_comic_comment_comic` (`comic_id`,`created_at`),
  KEY `idx_comic_comment_chapter` (`chapter_id`,`created_at`),
  KEY `idx_comic_comment_parent` (`parent_id`),
  KEY `idx_comic_comment_user` (`user_id`),
  CONSTRAINT `fk_comic_comment_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_parent_id` FOREIGN KEY (`parent_id`) REFERENCES `comic_comment` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_del_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_comic_comment_ref_upd_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_cre_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chapter`
--

DROP TABLE IF EXISTS `chapter`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chapter` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `title` varchar(150) NOT NULL,
  `slug` varchar(75) NOT NULL,
  `description` text DEFAULT NULL,
  `chapter_number` decimal(6,2) NOT NULL,
  `cover_image_key` varchar(255) DEFAULT NULL,
  `status` varchar(10) NOT NULL DEFAULT 'draft',
  `published_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  UNIQUE KEY `uq_comic_chapter_number` (`comic_id`,`chapter_number`),
  KEY `idx_chapter_status_created` (`status`,`created_at`),
  KEY `idx_chapter_comic_status` (`comic_id`,`status`),
  CONSTRAINT `fk_chapter_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chapter_ref_del_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_chapter_ref_upd_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chapter_ref_cre_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chapter_page`
--

DROP TABLE IF EXISTS `chapter_page`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chapter_page` (
  `id` varchar(36) NOT NULL,
  `chapter_id` varchar(36) NOT NULL,
  `page_number` int unsigned NOT NULL,
  `image_key` varchar(255) NOT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chapter_page_number` (`chapter_id`,`page_number`),
  KEY `idx_chapter_page_order` (`chapter_id`,`page_number`),
  CONSTRAINT `fk_chapter_page_ref_chapter_id` FOREIGN KEY (`chapter_id`) REFERENCES `chapter` (`id`) ON DELETE CASCADE,
CREATE TABLE `user_settings` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `is_public` tinyint(1) NOT NULL DEFAULT '0',
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  `is_userterms_approved` tinyint(1) NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `fk_user_settings_ref_user_id` (`user_id`),
  KEY `fk_user_settings_created_by` (`created_by`),
  KEY `fk_user_settings_updated_by` (`updated_by`),
  CONSTRAINT `fk_user_settings_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_settings_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_user_settings_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `voucher_log`
--

DROP TABLE IF EXISTS `voucher_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `voucher_log` (
  `id` varchar(36) NOT NULL,
  `code` varchar(15) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `task_id` varchar(36) NOT NULL,
  `karma` int NOT NULL DEFAULT '0',
  `mail` varchar(200) NOT NULL,
  `week` varchar(2) DEFAULT NULL,
  `month` varchar(10) NOT NULL,
  `claimed` tinyint(1) NOT NULL,
  `event` varchar(50) DEFAULT NULL,
  `description` varchar(50) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_voucher_log_ref_created_by` (`created_by`),
  KEY `fk_voucher_log_ref_task_id` (`task_id`),
  KEY `fk_voucher_log_ref_user_id` (`user_id`),
  CONSTRAINT `fk_voucher_log_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_voucher_log_ref_task_id` FOREIGN KEY (`task_id`) REFERENCES `task_list` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_voucher_log_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `wallet`
--

DROP TABLE IF EXISTS `wallet`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `wallet` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `karma` bigint NOT NULL DEFAULT '0',
  `karma_last_updated_at` datetime DEFAULT NULL,
  `coin` float NOT NULL DEFAULT '0',
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `fk_total_karma_ref_updated_by` (`updated_by`),
  KEY `fk_total_karma_ref_created_by` (`created_by`),
  CONSTRAINT `fk_total_karma_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_total_karma_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_total_karma_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `zone`
--

DROP TABLE IF EXISTS `zone`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `zone` (
  `id` varchar(36) NOT NULL,
  `name` varchar(75) NOT NULL,
  `state_id` varchar(36) NOT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_zone_ref_state_id` (`state_id`),
  KEY `fk_zone_ref_updated_by` (`updated_by`),
  KEY `fk_zone_ref_created_by` (`created_by`),
  CONSTRAINT `fk_zone_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_zone_ref_state_id` FOREIGN KEY (`state_id`) REFERENCES `state` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_zone_ref_updated_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `comic_comment`
--

DROP TABLE IF EXISTS `comic_comment`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `comic_comment` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `chapter_id` varchar(36) DEFAULT NULL,
  `parent_id` varchar(36) DEFAULT NULL,
  `user_id` varchar(36) NOT NULL,
  `message` text NOT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_comic_comment_comic` (`comic_id`,`created_at`),
  KEY `idx_comic_comment_chapter` (`chapter_id`,`created_at`),
  KEY `idx_comic_comment_parent` (`parent_id`),
  KEY `idx_comic_comment_user` (`user_id`),
  CONSTRAINT `fk_comic_comment_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_parent_id` FOREIGN KEY (`parent_id`) REFERENCES `comic_comment` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_del_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_comic_comment_ref_upd_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_comment_ref_cre_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chapter`
--

DROP TABLE IF EXISTS `chapter`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chapter` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `title` varchar(150) NOT NULL,
  `slug` varchar(75) NOT NULL,
  `description` text DEFAULT NULL,
  `chapter_number` decimal(6,2) NOT NULL,
  `cover_image_key` varchar(255) DEFAULT NULL,
  `status` varchar(10) NOT NULL DEFAULT 'draft',
  `published_at` datetime DEFAULT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `slug` (`slug`),
  UNIQUE KEY `uq_comic_chapter_number` (`comic_id`,`chapter_number`),
  KEY `idx_chapter_status_created` (`status`,`created_at`),
  KEY `idx_chapter_comic_status` (`comic_id`,`status`),
  CONSTRAINT `fk_chapter_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chapter_ref_del_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_chapter_ref_upd_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chapter_ref_cre_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chapter_page`
--

DROP TABLE IF EXISTS `chapter_page`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chapter_page` (
  `id` varchar(36) NOT NULL,
  `chapter_id` varchar(36) NOT NULL,
  `page_number` int unsigned NOT NULL,
  `image_key` varchar(255) NOT NULL,
  `deleted_at` datetime DEFAULT NULL,
  `deleted_by` varchar(36) DEFAULT NULL,
  `updated_by` varchar(36) NOT NULL,
  `updated_at` datetime NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chapter_page_number` (`chapter_id`,`page_number`),
  KEY `idx_chapter_page_order` (`chapter_id`,`page_number`),
  CONSTRAINT `fk_chapter_page_ref_chapter_id` FOREIGN KEY (`chapter_id`) REFERENCES `chapter` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chapter_page_ref_del_by` FOREIGN KEY (`deleted_by`) REFERENCES `user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_chapter_page_ref_upd_by` FOREIGN KEY (`updated_by`) REFERENCES `user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chapter_page_ref_cre_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

CREATE TABLE `comic_bookmark_link` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_comic_bookmark` (`comic_id`,`user_id`),
  KEY `fk_comic_bookmark_link_ref_created_by` (`created_by`),
  KEY `idx_comic_bookmark_user` (`user_id`),
  CONSTRAINT `fk_comic_bookmark_link_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_bookmark_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_comic_bookmark_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `comic_like_link` (
  `id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `created_by` varchar(36) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_comic_like` (`comic_id`,`user_id`),
  KEY `fk_comic_like_link_ref_created_by` (`created_by`),
  KEY `idx_comic_like_user` (`user_id`),
  CONSTRAINT `fk_comic_like_link_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_like_link_ref_created_by` FOREIGN KEY (`created_by`) REFERENCES `user` (`id`),
  CONSTRAINT `fk_comic_like_link_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `comic_reading_progress` (
  `id` varchar(36) NOT NULL,
  `user_id` varchar(36) NOT NULL,
  `comic_id` varchar(36) NOT NULL,
  `last_chapter_id` varchar(36) DEFAULT NULL,
  `last_page_number` int DEFAULT NULL,
  `updated_at` datetime NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_reading_progress` (`user_id`,`comic_id`),
  KEY `fk_comic_reading_progress_ref_comic_id` (`comic_id`),
  KEY `fk_comic_reading_progress_ref_last_chapter_id` (`last_chapter_id`),
  CONSTRAINT `fk_comic_reading_progress_ref_comic_id` FOREIGN KEY (`comic_id`) REFERENCES `comic` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_comic_reading_progress_ref_last_chapter_id` FOREIGN KEY (`last_chapter_id`) REFERENCES `chapter` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_comic_reading_progress_ref_user_id` FOREIGN KEY (`user_id`) REFERENCES `user` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

SET @@SESSION.SQL_LOG_BIN = @MYSQLDUMP_TEMP_LOG_BIN;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-03 23:24:46
