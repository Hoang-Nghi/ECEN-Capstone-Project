import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Linking } from 'react-native';

const FinancialEducationList = () => {
  const articles = [
    {
      title: "Understanding Personal Finance Basics",
      summary: "Learn the fundamental concepts of managing your money, budgeting, and saving for the future.",
      link: "https://example.com/personal-finance-basics"
    },
    {
      title: "Investing for Beginners: A Comprehensive Guide",
      summary: "Discover how to start investing, understand different investment vehicles, and build a diversified portfolio.",
      link: "https://example.com/investing-for-beginners"
    },
    {
      title: "Mastering Credit Scores and Reports",
      summary: "Explore the importance of credit scores, how they're calculated, and strategies to improve your creditworthiness.",
      link: "https://example.com/credit-scores-guide"
    },
    {
      title: "Retirement Planning: Securing Your Financial Future",
      summary: "Learn about various retirement accounts, planning strategies, and how to ensure a comfortable retirement.",
      link: "https://example.com/retirement-planning"
    },
    {
      title: "Navigating Tax Season: Tips and Strategies",
      summary: "Understand the basics of income tax, deductions, and how to maximize your tax returns efficiently.",
      link: "https://example.com/tax-season-tips"
    },
    {
      title: "Navigating Tax Season: Tips and Strategies",
      summary: "Understand the basics of income tax, deductions, and how to maximize your tax returns efficiently.",
      link: "https://example.com/tax-season-tips"
    },
    {
      title: "Navigating Tax Season: Tips and Strategies",
      summary: "Understand the basics of income tax, deductions, and how to maximize your tax returns efficiently.",
      link: "https://example.com/tax-season-tips"
    }
  ];

  const handleLinkPress = (url: string) => {
    Linking.openURL(url);
  };

  return (
    <ScrollView style={styles.container}>
      {articles.map((article, index) => (
        <TouchableOpacity 
          key={index} 
          style={styles.articleContainer}
          onPress={() => handleLinkPress(article.link)}
        >
          <Text style={styles.title}>{article.title}</Text>
          <Text style={styles.link}>{article.link}</Text>
          <Text style={styles.summary}>{article.summary}</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#f0f0f0',
  },
  articleContainer: {
    marginBottom: 20,
    padding: 10,
    backgroundColor: '#ffffff',
    borderRadius: 8,
    elevation: 2,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#1a0dab',
    marginBottom: 4,
  },
  link: {
    fontSize: 14,
    color: '#006621',
    marginBottom: 4,
  },
  summary: {
    fontSize: 14,
    color: '#545454',
  },
});

export default FinancialEducationList;