// Clinic products: oils, supplements and other things the clinic sells that are not medicines.
// Pick products, quantity, take payment and print the bill. Doctor and receptionist both see this page.
// SAFE TO EDIT: the words are in src/i18n/*.json under "products".
import { PlusOutlined } from '@ant-design/icons';
import { App, Button, Card, Empty, Input, InputNumber, Result, Segmented, Space, Table, Tag, Typography } from 'antd';
import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { api, errorMessage } from '../../api/client';
import type { PaymentMode, ProductRow } from '../../api/types';
import { useAuth } from '../../auth/AuthContext';
import { LiveSearch } from '../../components/LiveSearch';
import { ListEmpty } from '../../components/ListEmpty';
import { money } from '../medicines/shared';
import { PrintButton } from '../pharmacy/common';

type CartLine = { product: ProductRow; quantity: number };
type Done = { invoice: string; number: string; total_amount: string };

export default function ProductsPage() {
  const { t, i18n } = useTranslation();
  const { message } = App.useApp();
  const { can } = useAuth();
  const [rows, setRows] = useState<ProductRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const [query, setQuery] = useState('');
  const [cart, setCart] = useState<CartLine[]>([]);
  const [customer, setCustomer] = useState('');
  const [phone, setPhone] = useState('');
  const [mode, setMode] = useState<PaymentMode | 'later'>('cash');
  const [saving, setSaving] = useState(false);
  const [done, setDone] = useState<Done | null>(null);
  const canSell = can('products.sell');
  const lang = i18n.language.slice(0, 2);
  const nameOf = (p: ProductRow) => (lang === 'gu' && p.name_gu) || (lang === 'hi' && p.name_hi) || p.name;

  const load = useCallback(() => {
    setLoading(true);
    api.get<ProductRow[]>('/products/', { params: { q: query || undefined } })
      .then(({ data }) => { setRows(data); setFailed(false); })
      .catch(() => { setRows([]); setFailed(true); })
      .finally(() => setLoading(false));
  }, [query]);
  useEffect(() => { load(); }, [load]);

  const add = (p: ProductRow) => setCart((c) => {
    const have = c.find((l) => l.product.id === p.id);
    if (have) return c.map((l) => (l.product.id === p.id ? { ...l, quantity: Math.min(l.quantity + 1, Number(p.stock)) } : l));
    return [...c, { product: p, quantity: 1 }];
  });
  const total = cart.reduce((s, l) => s + Math.round(Number(l.product.price) * l.quantity * 100) / 100, 0);

  const sell = async () => {
    if (!cart.length) return;
    setSaving(true);
    try {
      // The earliest-expiry batches are used first (a line can need more than one batch)
      const items: { batch: string; quantity: number }[] = [];
      for (const l of cart) {
        let left = l.quantity;
        for (const b of l.product.batches) {
          if (left <= 0) break;
          const take = Math.min(left, Number(b.quantity));
          if (take > 0) { items.push({ batch: b.id, quantity: take }); left -= take; }
        }
      }
      const { data } = await api.post<Done>('/products/sell/', {
        items, customer_name: customer, customer_phone: phone,
        payment: mode === 'later' ? null : { mode, amount: total },
      });
      setDone(data);
      setCart([]); setCustomer(''); setPhone(''); setMode('cash');
      load();
    } catch (err) {
      message.error(errorMessage(err, t('common.saveFailed')));
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <div className="page-toolbar">
        <div>
          <Typography.Title level={3} style={{ margin: 0 }}>{t('products.title')}</Typography.Title>
          <div className="cell-sub">{t('products.subtitle')}</div>
        </div>
      </div>
      <div className="products-layout">
        <div>
          <div className="filter-bar">
            <LiveSearch placeholder={t('products.search')} onSearch={setQuery} loading={loading} width={300} />
          </div>
          <Table<ProductRow>
            rowKey="id" size="middle" loading={loading} dataSource={rows} pagination={false}
            locale={{ emptyText: <ListEmpty failed={failed} onRetry={load} text={t('products.none')} /> }}
            columns={[
              { title: t('products.product'), key: 'n', render: (_: unknown, p) => <div><b>{nameOf(p)}</b><div className="cell-sub">{[p.pack_size, p.sku].filter(Boolean).join(' · ')}</div></div> },
              { title: t('products.price'), dataIndex: 'price', align: 'right' as const, render: (v: string | null) => <span className="num">{money(v)}</span> },
              { title: t('products.stock'), dataIndex: 'stock', align: 'right' as const, render: (v: string) => (Number(v) > 0
                ? <span className="num">{Number(v)}</span> : <Tag color="red" bordered={false}>{t('products.out')}</Tag>) },
              ...(canSell ? [{
                title: '', key: 'a', width: 90, align: 'right' as const,
                render: (_: unknown, p: ProductRow) => <Button size="small" icon={<PlusOutlined />} disabled={Number(p.stock) <= 0} onClick={() => { setDone(null); add(p); }}>{t('products.add')}</Button>,
              }] : []),
            ]}
          />
        </div>

        {canSell && (
          <Card size="small" title={t('products.bill')} className="products-cart">
            {done && (
              <Result status="success" title={t('products.billMade', { number: done.number })} subTitle={money(done.total_amount)}
                extra={<Space><PrintButton id={done.invoice} size="middle" /><Button onClick={() => setDone(null)}>{t('products.newSale')}</Button></Space>} />
            )}
            {!done && !cart.length && <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={t('products.emptyCart')} />}
            {!done && cart.map((l) => (
              <div key={l.product.id} className="cart-line">
                <div style={{ flex: 1 }}><b>{nameOf(l.product)}</b><div className="cell-sub">{money(l.product.price)}</div></div>
                <InputNumber size="small" min={0} max={Number(l.product.stock)} value={l.quantity} style={{ width: 64 }}
                  onChange={(v) => setCart((c) => (v ? c.map((x) => (x.product.id === l.product.id ? { ...x, quantity: v } : x)) : c.filter((x) => x.product.id !== l.product.id)))} />
                <span className="num" style={{ width: 70, textAlign: 'right' }}>{money(Math.round(Number(l.product.price) * l.quantity * 100) / 100)}</span>
              </div>
            ))}
            {!done && cart.length > 0 && (
              <>
                <div className="cart-total"><span>{t('products.total')}</span><b className="num">{money(total)}</b></div>
                <Space direction="vertical" style={{ width: '100%' }} size={8}>
                  <Input placeholder={t('products.customer')} value={customer} maxLength={200} onChange={(e) => setCustomer(e.target.value)} />
                  <Input placeholder={t('products.phone')} value={phone} maxLength={10} onChange={(e) => setPhone(e.target.value.replace(/\D/g, ''))} />
                  <Segmented block value={mode} onChange={(v) => setMode(v as typeof mode)}
                    options={[{ value: 'cash', label: t('billing.cash') }, { value: 'upi', label: 'UPI' }, { value: 'card', label: t('billing.card') }, { value: 'later', label: t('products.payLater') }]} />
                  <Button type="primary" block loading={saving} onClick={sell} disabled={phone.length > 0 && phone.length !== 10}>{t('products.makeBill', { amount: money(total) })}</Button>
                </Space>
              </>
            )}
          </Card>
        )}
      </div>
    </>
  );
}
