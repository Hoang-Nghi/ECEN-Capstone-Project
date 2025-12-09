// hooks/purchases.tsx
import React, { useEffect, useState } from 'react';
import { FlatList, Image, StyleSheet, Text, View } from 'react-native';
import GifLoader from '../../components/GifLoader';
import { useAuth } from './useAuth';

const BASE_URL =
  process.env.EXPO_PUBLIC_API_BASE_URL ||
  'https://capstone-backend-1041336188288.us-central1.run.app';

interface Transaction {
  id: string;
  date: string;
  merchant_name: string;
  amount: number;
  category: string;
  logo_url?: string;
}

interface RecentTransactionsResponse {
  ok: boolean;
  count: number;
  transactions: Transaction[];
}

interface RecentPurchasesProps {
  maxVisible?: number; // e.g., 5 to show 5 at a time
  compact?: boolean;   // when true, behaves nicely inside a card
}

const RecentPurchases: React.FC<RecentPurchasesProps> = ({
  maxVisible,
  compact,
}) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);

  useEffect(() => {
    const fetchTransactions = async () => {
      if (!user) {
        setError('No authenticated user');
        setLoading(false);
        return;
      }

      try {
        const token = await user.getIdToken();
        const response = await fetch(
          `${BASE_URL}/api/analytics/transactions/recent?limit=20`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
              Accept: 'application/json',
            },
          }
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result: RecentTransactionsResponse = await response.json();
        setTransactions(result.transactions || []);
      } catch (err: any) {
        console.error('Error fetching recent transactions:', err);
        setError(err.message || 'Failed to load transactions');
      } finally {
        setLoading(false);
      }
    };

    fetchTransactions();
  }, [user]);

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr + 'T00:00:00Z');
      const now = new Date();
      const diffDays = Math.floor(
        (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
      );

      if (diffDays === 0) return 'Today';
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays} days ago`;

      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const renderPurchaseItem = ({ item }: { item: Transaction }) => (
    <View style={styles.purchaseItem}>
      <View style={styles.leftSection}>
        {item.logo_url ? (
          <Image
            source={{ uri: item.logo_url }}
            style={styles.logo}
            defaultSource={require('../../app/assets/placeholder-logo.jpg')}
          />
        ) : (
          <View style={styles.logoPlaceholder}>
            <Text style={styles.logoPlaceholderText}>
              {item.merchant_name.charAt(0).toUpperCase()}
            </Text>
          </View>
        )}
        <View style={styles.infoSection}>
          <Text style={styles.merchantName}>{item.merchant_name}</Text>
          <Text style={styles.categoryText}>{item.category}</Text>
          <Text style={styles.dateTime}>{formatDate(item.date)}</Text>
        </View>
      </View>
      <Text style={styles.cost}>${item.amount.toFixed(2)}</Text>
    </View>
  );

  const containerStyle = [
    styles.container,
    compact && styles.compactContainer,
  ];

  // If maxVisible is set, just slice the data – no inner scrolling.
  const displayedTransactions =
    maxVisible && maxVisible > 0
      ? transactions.slice(0, maxVisible)
      : transactions;

  if (loading) {
    return (
      <View style={containerStyle}>
        {!compact && <Text style={styles.header}>Recent Purchases</Text>}
        <View style={styles.loadingContainer}>
          <GifLoader />
          <Text style={styles.loadingText}>Loading transactions.</Text>
        </View>
      </View>
    );
  }

  if (error) {
    return (
      <View style={containerStyle}>
        {!compact && <Text style={styles.header}>Recent Purchases</Text>}
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>⚠️ {error}</Text>
          <Text style={styles.hintText}>
            Unable to load your transactions
          </Text>
        </View>
      </View>
    );
  }

  if (transactions.length === 0) {
    return (
      <View style={containerStyle}>
        {!compact && <Text style={styles.header}>Recent Purchases</Text>}
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyText}>No transactions yet</Text>
          <Text style={styles.hintText}>
            Link your bank account to start tracking purchases
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={containerStyle}>
      {!compact && (
        <>
          <Text style={styles.header}>Recent Purchases</Text>
          <Text style={styles.subheader}>
            {transactions.length} transactions
          </Text>
        </>
      )}

      <FlatList
        data={displayedTransactions}
        renderItem={renderPurchaseItem}
        keyExtractor={(item) => item.id}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.listContent}
        // 🔑 Important: disable inner scrolling to avoid nested VirtualizedList warning
        scrollEnabled={false}
        nestedScrollEnabled={false}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#f5f5f5',
  },
  compactContainer: {
    flex: 0,
    padding: 0,
    backgroundColor: 'transparent',
  },
  header: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 4,
    color: '#333',
  },
  subheader: {
    fontSize: 14,
    color: '#888',
    marginBottom: 16,
  },
  listContent: {
    paddingBottom: 16,
  },
  purchaseItem: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 14,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  leftSection: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  logo: {
    width: 40,
    height: 40,
    borderRadius: 20,
    marginRight: 12,
  },
  logoPlaceholder: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#00b140',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  logoPlaceholderText: {
    color: 'white',
    fontSize: 18,
    fontWeight: 'bold',
  },
  infoSection: {
    flex: 1,
  },
  merchantName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 2,
  },
  categoryText: {
    fontSize: 13,
    color: '#00b140',
    marginBottom: 2,
  },
  dateTime: {
    fontSize: 12,
    color: '#999',
  },
  cost: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginLeft: 8,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 12,
    color: '#666',
    fontSize: 14,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    color: '#e74c3c',
    fontSize: 16,
    marginBottom: 8,
    textAlign: 'center',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    color: '#333',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 8,
  },
  hintText: {
    color: '#888',
    fontSize: 14,
    textAlign: 'center',
  },
});

export default RecentPurchases;
