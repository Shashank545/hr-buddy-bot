import { useRef, useState } from "react";
import {
    Checkbox,
    ChoiceGroup,
    DefaultButton,
    IChoiceGroupOption,
    Panel,
    SpinButton,
    Spinner,
    Slider
} from "@fluentui/react";
import React from "react";

import styles from "./OneShot.module.css";

import { askApi, Approaches, AskResponse, AskRequest, Deployments, SearchOptions, ACSIndex } from "../../api";
import { Answer, AnswerError } from "../../components/Answer";
import { QuestionInput } from "../../components/QuestionInput";
import { ExampleList } from "../../components/Example";
import { AnalysisPanel, AnalysisPanelTabs } from "../../components/AnalysisPanel";
import { SettingsButton } from "../../components/SettingsButton/SettingsButton";

const OneShot = () => {
    const [isConfigPanelOpen, setIsConfigPanelOpen] = useState(false);
    const [approach, setApproach] = useState<Approaches>(Approaches.RetrieveRead);
    const [deployment, setDeployment] = useState<Deployments>(Deployments.Gpt35Turbo);
    const [index, setIndex] = useState<ACSIndex>(ACSIndex.IFRS);
    const [searchOption, setSearchOption] = useState<SearchOptions>(SearchOptions.BM25);
    const [retrieveCount, setRetrieveCount] = useState<number>(3);
    const [temperature, setTemperature] = useState<number>(0.6);
    const [useSemanticCaptions, setUseSemanticCaptions] = useState<boolean>(false);

    const lastQuestionRef = useRef<string>("");

    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [error, setError] = useState<unknown>();
    const [answer, setAnswer] = useState<AskResponse>();

    const [activeCitation, setActiveCitation] = useState<string>();
    const [activeAnalysisPanelTab, setActiveAnalysisPanelTab] = useState<AnalysisPanelTabs | undefined>(undefined);

    const makeApiRequest = async (question: string) => {
        lastQuestionRef.current = question;

        error && setError(undefined);
        setIsLoading(true);
        setActiveCitation(undefined);
        setActiveAnalysisPanelTab(undefined);

        try {
            const request: AskRequest = {
                question,
                approach,
                deployment,
                index,
                overrides: {
                    top: retrieveCount,
                    semanticCaptions: useSemanticCaptions,
                    searchOption: Object.values(SearchOptions).indexOf(searchOption),
                    temperature: temperature
                }
            };
            const result = await askApi(request);
            setAnswer(result);
        } catch (e) {
            setError(e);
        } finally {
            setIsLoading(false);
        }
    };

    const onRetrieveCountChange = (_ev?: React.SyntheticEvent<HTMLElement, Event>, newValue?: string) => {
        setRetrieveCount(parseInt(newValue || "3"));
    };

    const onTemperatureChange = (newValue: any) => {
    };

    const onApproachChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, option?: IChoiceGroupOption) => {
        setApproach((option?.key as Approaches) || Approaches.RetrieveRead);
    };

    const onDeploymentChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, option?: IChoiceGroupOption) => {
        setDeployment((option?.key as Deployments) || Deployments.Gpt35Turbo);
    };

    const onSearchOptionChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, option?: IChoiceGroupOption) => {
        setSearchOption((option?.key as SearchOptions) || SearchOptions.BM25);
    };

    const onUseSemanticCaptionsChange = (_ev?: React.FormEvent<HTMLElement | HTMLInputElement>, checked?: boolean) => {
        setUseSemanticCaptions(!!checked);
    };

    const onExampleClicked = (example: string) => {
        makeApiRequest(example);
    };

    const onShowCitation = (citation: string) => {
        if (activeCitation === citation && activeAnalysisPanelTab === AnalysisPanelTabs.CitationTab) {
            setActiveAnalysisPanelTab(undefined);
        } else {
            setActiveCitation(citation);
            setActiveAnalysisPanelTab(AnalysisPanelTabs.CitationTab);
        }
    };

    const onToggleTab = (tab: AnalysisPanelTabs) => {
        if (activeAnalysisPanelTab === tab) {
            setActiveAnalysisPanelTab(undefined);
        } else {
            setActiveAnalysisPanelTab(tab);
        }
    };

    const onIndexChange = (index_: ACSIndex) => {
        setIndex(index_);
    };

    const approaches: IChoiceGroupOption[] = [
        {
            key: Approaches.RetrieveRead,
            text: "Approach 1",
            disabled: false,
            onRenderField: (props, render) => {
                return (
                    <div className={styles.oneshotApproachOption}>
                        {render!(props)}
                        <a className={styles.oneshotApproachOptionDescription}>
                            Retrieve → Read
                        </a>
                    </div>
                );
            }
        },
        {
            key: Approaches.RetrieveReformulateRetrieveRead,
            text: "Approach 2",
            disabled: false,
            onRenderField: (props, render) => {
                return (
                    <div className={styles.oneshotApproachOption}>
                        {render!(props)}
                        <a className={styles.oneshotApproachOptionDescription}>
                            Retrieve → Reformulate → Retrieve → Read
                        </a>
                    </div>
                );
            }
        },
        {
            key: Approaches.RetrieveReadRead,
            text: "Approach 3",
            disabled: false,
            onRenderField: (props, render) => {
                return (
                    <div className={styles.oneshotApproachOption}>
                        {render!(props)}
                        <a className={styles.oneshotApproachOptionDescription}>
                            Retrieve → Read → Read
                        </a>
                    </div>
                );
            }
        },
        {
            key: Approaches.RetrieveReadRetry,
            text: "Approach 4",
            disabled: false,
            onRenderField: (props, render) => {
                return (
                    <div className={styles.oneshotApproachOption}>
                        {render!(props)}
                        <a className={styles.oneshotApproachOptionDescription}>
                            Approach 1 → Check → Approach 2
                        </a>
                    </div>
                );
            }
        }
    ];

    const deployments: IChoiceGroupOption[] = [
        {
            key: Deployments.Gpt35Turbo,
            text: Deployments.Gpt35Turbo,
            disabled: false,
            onRenderField: (props, render) => {
                return (
                    <div className={styles.oneshotDeploymentOption}>
                        {render!(props)}
                        <a className={styles.oneshotDeploymentOptionPrice}>(Prompt & Completion) ¥0.281 per 1,000 tokens</a>
                    </div>
                );
            }
        },
        {
            key: Deployments.Gpt4,
            text: Deployments.Gpt4,
            disabled: false,
            onRenderField: (props, render) => {
                return (
                    <div className={styles.oneshotDeploymentOption}>
                        {render!(props)}
                        <a className={styles.oneshotDeploymentOptionPrice}>
                            (Prompt) ¥4.215 per 1,000 tokens <br />
                            (Completion) ¥8.430 per 1,000 tokens
                        </a>
                    </div>
                );
            }
        }
    ];

    const searchOptions: IChoiceGroupOption[] = [
        {
            key: SearchOptions.BM25,
            text: SearchOptions.BM25,
            disabled: false
        },
        {
            key: SearchOptions.Semantic,
            text: SearchOptions.Semantic,
            disabled: false
        },
        {
            key: SearchOptions.Vector,
            text: "Embeddings",
            disabled: false
        },
        {
            key: SearchOptions.VectorBM25,
            text: `Hybrid: Embeddings + ${SearchOptions.BM25}`,
            disabled: false
        },
        {
            key: SearchOptions.VectorSemantic,
            text: `Hybrid: Embeddings + ${SearchOptions.Semantic}`,
            disabled: false
        }
    ];

    return (
        <div className={styles.oneshotContainer}>
            <div className={styles.oneshotTopSection}>
                <SettingsButton className={styles.settingsButton} onClick={() => setIsConfigPanelOpen(!isConfigPanelOpen)} />
                <h1 className={styles.oneshotTitle}>Hello! How can I help you?</h1>
                <div className={styles.oneshotQuestionInput}>
                    <QuestionInput
                        placeholder={"Example: What should I do to take personal time off?"}
                        disabled={isLoading}
                        onSend={question => makeApiRequest(question)}
                        currentQuestion={lastQuestionRef.current}
                    />
                </div>
            </div>
            <div className={styles.oneshotBottomSection}>
                {isLoading && <Spinner label="Generating answer" />}
                {!lastQuestionRef.current && <ExampleList onExampleClicked={onExampleClicked} />}
                {!isLoading && answer && !error && (
                    <div className={styles.oneshotAnswerContainer}>
                        <Answer
                            answer={answer}
                            onCitationClicked={x => onShowCitation(x)}
                            onThoughtProcessClicked={() => onToggleTab(AnalysisPanelTabs.ThoughtProcessTab)}
                            onSupportingContentClicked={() => onToggleTab(AnalysisPanelTabs.SupportingContentTab)}
                            onMonitoringClicked={() => onToggleTab(AnalysisPanelTabs.Monitoring)}
                        />
                    </div>
                )}
                {error ? (
                    <div className={styles.oneshotAnswerContainer}>
                        <AnswerError error={error.toString()} onRetry={() => makeApiRequest(lastQuestionRef.current)} />
                    </div>
                ) : null}
                {activeAnalysisPanelTab && answer && (
                    <AnalysisPanel
                        className={styles.oneshotAnalysisPanel}
                        activeCitation={activeCitation}
                        onActiveTabChanged={x => onToggleTab(x)}
                        citationHeight="600px"
                        answer={answer}
                        activeTab={activeAnalysisPanelTab}
                    />
                )}
            </div>

            <Panel
                headerText="Settings"
                isOpen={isConfigPanelOpen}
                onDismiss={() => setIsConfigPanelOpen(false)}
                closeButtonAriaLabel="Close"
                onRenderFooterContent={() => <DefaultButton onClick={() => setIsConfigPanelOpen(false)}>Close</DefaultButton>}
                isFooterAtBottom={true}
                isLightDismiss
            >
                <ChoiceGroup
                    className={styles.oneshotSettingsSeparator}
                    label="1. Prompting Strategy"
                    options={approaches}
                    defaultSelectedKey={approach}
                    onChange={onApproachChange}
                />

                <SpinButton
                    className={styles.oneshotSettingsSeparator}
                    label="2. Number of knowledge items to generate responses"
                    min={1}
                    max={50}
                    defaultValue={retrieveCount.toString()}
                    onChange={onRetrieveCountChange}
                />

                <ChoiceGroup
                    className={styles.oneshotSettingsSeparator}
                    label="3. Configuration for the Search Service (ACS)"
                    options={searchOptions}
                    defaultSelectedKey={searchOption}
                    onChange={onSearchOptionChange}
                />

                <Checkbox
                    className={styles.oneshotSettingsSeparator}
                    checked={useSemanticCaptions}
                    label="4. View verbose text predicted by search service"
                    onChange={onUseSemanticCaptionsChange}
                    boxSide="end"
                    disabled={![SearchOptions.Semantic, SearchOptions.VectorSemantic].includes(searchOption)}
                />

                <Slider
                    className={styles.oneshotSettingsSeparator}
                    label="5. Temperature parameters of generative AI"
                    min={0.0}
                    max={1.0}
                    step={0.1}
                    defaultValue={temperature}
                    onChange={onTemperatureChange}
                />

                <ChoiceGroup
                    className={styles.oneshotSettingsSeparator}
                    label="6. Generative AI Models"
                    options={deployments}
                    defaultSelectedKey={deployment}
                    onChange={onDeploymentChange}
                />
            </Panel>
        </div>
    );
};

export default OneShot;
