-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Aug 29, 2025 at 05:31 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `ExamSeatAllowtment`
--

-- --------------------------------------------------------

--
-- Table structure for table `RoomInfo`
--

CREATE TABLE `RoomInfo` (
  `RoomId` varchar(20) NOT NULL,
  `totalCapacity` int(50) DEFAULT NULL,
  `BenchPerCol` varchar(10) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `RoomInfo`
--

INSERT INTO `RoomInfo` (`RoomId`, `totalCapacity`, `BenchPerCol`) VALUES
('1', 110, '18,18,19'),
('13', 36, '9,9'),
('15', 72, '12,12,12'),
('16', 54, '9,9,9'),
('18', 16, '4,4'),
('20', 78, '12,12,15'),
('3A', 28, '6,4,4'),
('Sister Nivedita Hall', 88, '22,22'),
('Tejasananda Hall', 60, '15,15');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `RoomInfo`
--
ALTER TABLE `RoomInfo`
  ADD PRIMARY KEY (`RoomId`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
