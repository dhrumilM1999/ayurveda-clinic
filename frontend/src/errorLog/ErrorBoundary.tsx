// If a screen crashes, show a friendly message (not a blank page) and tell the Error log.
// SAFE TO EDIT: the words are in src/i18n/*.json under "errorLog.crash".
import { Button, Result, Space } from 'antd';
import { Component, type ErrorInfo, type ReactNode } from 'react';
import i18n from '../i18n';
import { addStep, lastErrorCode, sendReport } from './tracker';

interface Props { children: ReactNode; resetKey: string }
interface State { failed: boolean; code: string }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false, code: '' };

  static getDerivedStateFromError(): Partial<State> {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    addStep('error', error.message);
    sendReport({ kind: 'react', message: error.message, details: `${error.stack ?? ''}\n${info.componentStack ?? ''}` })
      .then(() => this.setState({ code: lastErrorCode() }));
  }

  componentDidUpdate(prev: Props) {
    // Opening another page gives the app a fresh start
    if (this.state.failed && prev.resetKey !== this.props.resetKey) this.setState({ failed: false, code: '' });
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <Result
        status="warning"
        title={i18n.t('errorLog.crash.title')}
        subTitle={`${i18n.t('errorLog.crash.text')}${this.state.code ? ` ${i18n.t('errorLog.crash.code', { code: this.state.code })}` : ''}`}
        extra={(
          <Space>
            <Button type="primary" onClick={() => window.location.reload()}>{i18n.t('errorLog.crash.reload')}</Button>
            <Button onClick={() => { window.location.href = '/'; }}>{i18n.t('errorLog.crash.home')}</Button>
          </Space>
        )}
      />
    );
  }
}
