import { Pivot, PivotItem } from "@fluentui/react";
import { JsonView } from 'react-json-view-lite';
import styles from "./AnalysisPanel.module.css";
import "./AnalysisPanel.css"

import { SupportingContent } from "../SupportingContent";
import { AskResponse } from "../../api";
import { AnalysisPanelTabs } from "./AnalysisPanelTabs";

interface Props {
    className: string;
    activeTab: AnalysisPanelTabs;
    onActiveTabChanged: (tab: AnalysisPanelTabs) => void;
    activeCitation: string | undefined;
    citationHeight: string;
    answer: AskResponse;
}

const pivotItemDisabledStyle = { disabled: true, style: { color: "grey" } };

export const AnalysisPanel = ({ answer, activeTab, className, onActiveTabChanged }: Props) => {
    const isDisabledMonitoringTab: boolean = !answer.monitoring;
    const isDisabledThoughtProcessTab: boolean = !answer.thoughts;
    const isDisabledSupportingContentTab: boolean = !answer.data_points.length;

    return (
        <Pivot
            className={className}
            selectedKey={activeTab}
            onLinkClick={pivotItem => pivotItem && onActiveTabChanged(pivotItem.props.itemKey! as AnalysisPanelTabs)}
        >
            <PivotItem
                itemKey={AnalysisPanelTabs.Monitoring}
                headerText="モニタリング"
                headerButtonProps={isDisabledMonitoringTab ? pivotItemDisabledStyle : undefined}
            >
                <div className={styles.thoughtProcess}>
                        <div>
                            <h4>経過時間</h4>
                            <p>合計: <u>{answer.monitoring.time.total} 秒</u></p>
                            <ul>
                                {answer.monitoring.time.items.map((item, index)=> (
                                    <li key={`time-item-${index}`}>{item.label}: {item.value} 秒</li>
                                ))}
                            </ul>
                        </div>
                        <div>
                            <h4>推定コスト</h4>
                            <p>合計: <u>{answer.monitoring.cost.total} 円</u></p>
                            <ul>
                                {answer.monitoring.cost.items.map((item, index)=> (
                                    <li key={`cost-item-${index}`}>{item.label}: {item.value} 円</li>
                                ))}
                            </ul>
                        </div>
                        <div>
                            <h4>利用状況</h4>
                            <ul>
                                {answer.monitoring.usage.map((item, index)=> (
                                    <li key={`thought-process-${index}`}>
                                        {item.label}
                                        <ul>
                                            <li>完了トークン: {item.value.completion_tokens}</li>
                                            <li>プロンプトトークン: {item.value.prompt_tokens}</li>
                                            <li>合計トークン: {item.value.total_tokens}</li>
                                        </ul>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
            </PivotItem>
            <PivotItem
                itemKey={AnalysisPanelTabs.ThoughtProcessTab}
                headerText="推論過程"
                headerButtonProps={isDisabledThoughtProcessTab ? pivotItemDisabledStyle : undefined}
            >
                <div className={styles.thoughtProcess}>
                    {answer.thoughts.map((item, index)=> (
                        <div key={`thought-process-${index}`}>
                            <h4>{`${index+1}. ${item.label}`}</h4>
                            {
                                typeof item.value === 'object' 
                                ? <JsonView data={item.value} shouldInitiallyExpand={(level) => false} />
                                : <p className={styles.thoughtProcessDescription}>{item.value}</p>
                            }
                        </div>
                    ))}
                </div>
            </PivotItem>
            <PivotItem
                itemKey={AnalysisPanelTabs.SupportingContentTab}
                headerText="補足コンテント"
                headerButtonProps={isDisabledSupportingContentTab ? pivotItemDisabledStyle : undefined}
            >
                <SupportingContent supportingContent={answer.data_points} />
            </PivotItem>
        </Pivot>
    );
};
